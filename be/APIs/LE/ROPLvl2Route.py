from typing import List
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from APIs.Core import get_db, get_current_user
from APIs.LE.ROPLvl1Route import get_lvl1_by_id
from Models.LE.ROPLvl2 import ROPLvl2, ROPLvl2Distribution
from Models.Admin.User import User, UserProjectAccess
from Models.Admin.AuditLog import AuditLog
from Schemas.LE.ROPLvl2Schema import ROPLvl2Create, ROPLvl2Out

logger = logging.getLogger(__name__)
ROPLvl2router = APIRouter(prefix="/rop-lvl2", tags=["ROP Lvl2"])


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
# Helpers
# ----------------------------
def check_project_access(current_user: User, pid_po: str, db: Session, required_permission: str = "view"):
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


# ----------------------------
# CRUD with admin controls
# ----------------------------
@ROPLvl2router.post("/create", response_model=ROPLvl2Out)
def create_lvl2(data: ROPLvl2Create, request: Request = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.name != "senior_admin" and current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only senior admins can create Lvl1")

    new_lvl2 = ROPLvl2(**data.dict(exclude={"distributions"}))
    db.add(new_lvl2)
    db.commit()
    db.refresh(new_lvl2)

    for dist in data.distributions:
        db.add(ROPLvl2Distribution(
            lvl2_id=new_lvl2.id,
            month=dist.month,
            year=dist.year,
            allocated_quantity=dist.allocated_quantity
        ))
    db.commit()
    db.refresh(new_lvl2)

    roplvl1_data = get_lvl1_by_id(new_lvl2.lvl1_id, db=db, current_user=current_user)
    roplvl1_data.price = (roplvl1_data.price + ((new_lvl2.price * new_lvl2.total_quantity) / roplvl1_data.total_quantity))
    db.commit()

    # Create audit log
    if request:
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="create",
            resource_type="ROPLvl2",
            resource_id=new_lvl2.id,
            resource_name=new_lvl2.item_name,
            details=json.dumps({"project_id": data.project_id, "lvl1_id": data.lvl1_id}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

    return new_lvl2


@ROPLvl2router.get("/", response_model=List[ROPLvl2Out])
def get_all_lvl2(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.name == "senior_admin":
        return db.query(ROPLvl2).all()
    accesses = db.query(UserProjectAccess).filter(UserProjectAccess.user_id == current_user.id).all()
    if not accesses:
        return []
    project_ids = [a.project_id for a in accesses]
    return db.query(ROPLvl2).filter(ROPLvl2.project_id.in_(project_ids)).all()


@ROPLvl2router.get("/by-lvl1/{lvl1_id}", response_model=List[ROPLvl2Out])
def get_lvl2_by_lvl1(lvl1_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = get_lvl1_by_id(lvl1_id, db=db, current_user=current_user)
    if not check_project_access(current_user, lvl1.project_id, db, "view"):
        raise HTTPException(status_code=403, detail="Not authorized to view Lvl2 for this Lvl1")
    return db.query(ROPLvl2).filter(ROPLvl2.lvl1_id == lvl1_id).all()


@ROPLvl2router.get("/{id}", response_model=ROPLvl2Out)
def get_lvl2_by_id(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    if not check_project_access(current_user, lvl2.project_id, db, "view"):
        raise HTTPException(status_code=403, detail="Not authorized to view this Lvl2")
    return lvl2


@ROPLvl2router.put("/update/{id}", response_model=ROPLvl2Out)
def update_lvl2(id: str, data: ROPLvl2Create, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    if not check_project_access(current_user, lvl2.project_id, db, "edit"):
        raise HTTPException(status_code=403, detail="Not authorized to update this Lvl2")

    for key, value in data.dict(exclude={"distributions"}).items():
        setattr(lvl2, key, value)

    db.query(ROPLvl2Distribution).filter(ROPLvl2Distribution.lvl2_id == id).delete()
    for dist in data.distributions:
        db.add(ROPLvl2Distribution(
            lvl2_id=id,
            month=dist.month,
            year=dist.year,
            allocated_quantity=dist.allocated_quantity
        ))

    db.commit()
    db.refresh(lvl2)

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="ROPLvl2",
        resource_id=id,
        resource_name=lvl2.item_name,
        details=json.dumps({"project_id": lvl2.project_id}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return lvl2


@ROPLvl2router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lvl2(id: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    if not check_project_access(current_user, lvl2.project_id, db, "all"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this Lvl2")

    # Store for audit
    item_name = lvl2.item_name
    project_id = lvl2.project_id

    db.delete(lvl2)
    db.commit()

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="ROPLvl2",
        resource_id=id,
        resource_name=item_name,
        details=json.dumps({"project_id": project_id}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )
