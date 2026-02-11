from typing import List
import json
import logging
from fastapi import Depends, HTTPException, APIRouter, status, Request
from sqlalchemy.orm import Session

from APIs.Core import get_db, get_current_user
from Models.LE.ROPLvl1 import ROPLvl1
from Models.LE.ROPLvl2 import ROPLvl2
from Models.Admin.User import User, UserProjectAccess
from Models.Admin.AuditLog import AuditLog
from Schemas.LE.ROPLvl1Schema import ROPLvl1Out, ROPLvl1Create

logger = logging.getLogger(__name__)
ROPLvl1router = APIRouter(prefix="/rop-lvl1", tags=["ROP Lvl1"])


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_audit_log_sync(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: str = None,
    resource_name: str = None,
    details: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Create an audit log entry (synchronous version)."""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


# ----------------------------
# Helper functions
# ----------------------------
def check_project_access(current_user: User, pid_po: str, db: Session, required_permission: str = "view"):
    """Check if user has required access level to a project."""
    if current_user.role.name == "senior_admin":
        return True

    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ropproject_id == pid_po
    ).first()

    if not access:
        return False

    hierarchy = {"view": ["view", "edit", "all"], "edit": ["edit", "all"], "all": ["all"]}
    return access.permission_level in hierarchy.get(required_permission, [])


def update_lvl1_dates(lvl1_id: str, db: Session):
    """Auto-sync start/end dates from linked lvl2 entries."""
    lvl2_items = db.query(ROPLvl2).filter(ROPLvl2.lvl1_id == lvl1_id).all()
    if not lvl2_items:
        return
    earliest = min((i.start_date for i in lvl2_items if i.start_date), default=None)
    latest = max((i.end_date for i in lvl2_items if i.end_date), default=None)
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == lvl1_id).first()
    if lvl1:
        lvl1.start_date = earliest
        lvl1.end_date = latest
        db.commit()


# ----------------------------
# CRUD with admin controls
# ----------------------------
@ROPLvl1router.post("/create", response_model=ROPLvl1Out)
def create_lvl1(
    data: ROPLvl1Create,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "senior_admin" and current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only senior admins can create Lvl1")

    new_lvl1 = ROPLvl1(**data.dict())
    db.add(new_lvl1)
    db.commit()
    db.refresh(new_lvl1)

    # Create audit log
    if request:
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="create",
            resource_type="ROPLvl1",
            resource_id=new_lvl1.id,
            resource_name=new_lvl1.item_name,
            details=json.dumps({"project_id": data.project_id}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

    return new_lvl1


@ROPLvl1router.get("/", response_model=List[ROPLvl1Out])
def get_all_lvl1(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all ROP Level 1 entries with pagination.

    OPTIMIZED: Added pagination (skip/limit) to prevent loading unlimited records.
    """
    if current_user.role.name == "senior_admin":
        # OPTIMIZED: Added pagination for senior admin
        # MSSQL requires ORDER BY when using OFFSET/LIMIT
        return db.query(ROPLvl1).order_by(ROPLvl1.id).offset(skip).limit(limit).all()

    # filter by accessible projects
    accesses = db.query(UserProjectAccess).filter(UserProjectAccess.user_id == current_user.id).all()
    if not accesses:
        return []
    project_ids = [a.project_id for a in accesses]
    # OPTIMIZED: Added pagination for filtered results
    # MSSQL requires ORDER BY when using OFFSET/LIMIT
    return db.query(ROPLvl1).filter(ROPLvl1.project_id.in_(project_ids)).order_by(ROPLvl1.id).offset(skip).limit(limit).all()


@ROPLvl1router.get("/by-project/{pid_po}", response_model=List[ROPLvl1Out])
def get_lvl1_by_project(
    pid_po: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get ROP Level 1 entries by project with pagination.

    OPTIMIZED: Added pagination (skip/limit) to prevent loading unlimited records.
    """
    if not check_project_access(current_user, pid_po, db, "view"):
        raise HTTPException(status_code=403, detail="Not authorized to view this project's Lvl1")
    # OPTIMIZED: Added pagination
    # MSSQL requires ORDER BY when using OFFSET/LIMIT
    return db.query(ROPLvl1).filter(ROPLvl1.project_id == pid_po).order_by(ROPLvl1.id).offset(skip).limit(limit).all()


@ROPLvl1router.get("/{id}", response_model=ROPLvl1Out)
def get_lvl1_by_id(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    if not check_project_access(current_user, lvl1.project_id, db, "view"):
        raise HTTPException(status_code=403, detail="Not authorized to view this Lvl1")
    return lvl1


@ROPLvl1router.put("/update/{id}", response_model=ROPLvl1Out)
def update_lvl1(id: str, data: ROPLvl1Create, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")

    if not check_project_access(current_user, lvl1.project_id, db, "edit"):
        raise HTTPException(status_code=403, detail="Not authorized to update this Lvl1")

    for field, value in data.dict().items():
        setattr(lvl1, field, value)
    db.commit()
    db.refresh(lvl1)

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="ROPLvl1",
        resource_id=id,
        resource_name=lvl1.item_name,
        details=json.dumps({"project_id": lvl1.project_id}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return lvl1


@ROPLvl1router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lvl1(id: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")

    if not check_project_access(current_user, lvl1.project_id, db, "all"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this Lvl1")

    # Store for audit
    item_name = lvl1.item_name
    project_id = lvl1.project_id

    db.delete(lvl1)
    db.commit()

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="ROPLvl1",
        resource_id=id,
        resource_name=item_name,
        details=json.dumps({"project_id": project_id}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )
