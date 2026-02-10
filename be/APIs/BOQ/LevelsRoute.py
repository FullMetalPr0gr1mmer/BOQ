from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import json
import logging

from APIs.Core import get_db, get_current_user
from Models.BOQ.Levels import Lvl1
from Models.Admin.User import User
from Models.Admin.AuditLog import AuditLog
from Schemas.BOQ.LevelsSchema import (
    Lvl1Create, Lvl1Out,
)

logger = logging.getLogger(__name__)
levelsRouter = APIRouter(tags=["Levels"])


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

# ---------------------------- Level 1 ----------------------------

@levelsRouter.post("/create-lvl1")
def create_lvl1_entry(data: Lvl1Create, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = Lvl1(
        project_id=data.project_id,
        project_name=data.project_name,
        item_name=data.item_name,
        region=data.region,
        quantity=data.quantity,
        price=data.price
    )
    lvl1.set_service_type(data.service_type)
    db.add(lvl1)
    db.commit()
    db.refresh(lvl1)

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="Lvl1",
        resource_id=str(lvl1.id),
        resource_name=data.item_name,
        details=json.dumps({"project_id": data.project_id, "project_name": data.project_name}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return lvl1

@levelsRouter.get("/get-lvl1")
def get_all_lvl1(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all Level 1 entries with pagination.

    OPTIMIZED: Added pagination (skip/limit) to prevent loading unlimited records.
    """
    # OPTIMIZED: Added offset and limit for pagination
    # MSSQL requires ORDER BY when using OFFSET/LIMIT
    entries = db.query(Lvl1).order_by(Lvl1.id).offset(skip).limit(limit).all()
    return [
        Lvl1Out(
            id=entry.id,
            project_id=entry.project_id,
            project_name=entry.project_name,
            item_name=entry.item_name,
            region=entry.region if entry.region else "Main",
            quantity=entry.quantity,
            price=entry.price,
            service_type=entry.get_service_type()
        )
        for entry in entries
    ]

@levelsRouter.put("/update-lvl1/{id}")
def update_lvl1(id: int, data: Lvl1Create, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = db.query(Lvl1).filter(Lvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    lvl1.project_id = data.project_id
    lvl1.project_name = data.project_name
    lvl1.item_name = data.item_name
    lvl1.region = data.region
    lvl1.quantity = data.quantity
    lvl1.price = data.price
    lvl1.set_service_type(data.service_type)
    db.commit()
    db.refresh(lvl1)

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="Lvl1",
        resource_id=str(id),
        resource_name=data.item_name,
        details=json.dumps({"project_id": data.project_id}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return lvl1

@levelsRouter.delete("/delete-lvl1/{id}")
def delete_lvl1(id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = db.query(Lvl1).filter(Lvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")

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
        resource_type="Lvl1",
        resource_id=str(id),
        resource_name=item_name,
        details=json.dumps({"project_id": project_id}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return {"msg": "Lvl1 entry deleted"}
