# routes/adminRoute.py
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import desc, or_, and_
from sqlalchemy.orm import Session
from APIs.Core import get_current_user, get_db

logger = logging.getLogger(__name__)
from Models.Admin.AuditLog import AuditLog
from Models.Admin.User import User, UserProjectAccess, Role
from Models.BOQ.Project import Project
from Models.LE.ROPProject import ROPProject
from Models.RAN.RANProject import RanProject
import importlib
du_project_module = importlib.import_module("Models.DU.DU_Project")
DUProject = du_project_module.DUProject
from Schemas.Admin.AccessSchema import (
    UserProjectAccessCreate,
    UserProjectAccessResponse,
    UserProjectAccessUpdate,
    UserWithProjectsResponse,
    ApprovalStageAccessUpdate,
    ApprovalStageAccessResponse
)
from Schemas.Admin.LogSchema import AuditLogResponse, PaginatedAuditLogResponse
from Schemas.Admin.UserSchema import UserRoleUpdateResponse, UserRoleUpdateRequest
from utils.access_control import (
    get_all_user_accessible_project_ids,
    get_all_accessible_project_ids_flat,
    get_users_sharing_projects,
    can_admin_manage_project
)

adminRoute = APIRouter(prefix="/audit-logs",tags=["Admin"])

# Allowed roles for admin operations (senior_admin has full access, admin has project-scoped access)
ADMIN_ROLES = ["senior_admin", "admin"]

# ===========================
# HELPER FUNCTIONS
# ===========================

async def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    project_id: Optional[str] = None,
    section: Optional[int] = None
):
    """Create an audit log entry with optional project tracking for access control."""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        project_id=project_id,
        section=section
    )
    db.add(audit_log)
    db.commit()
    return audit_log


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ===========================
# PROJECT ACCESS MANAGEMENT
# ===========================

@adminRoute.post("/grant_project_access", response_model=UserProjectAccessResponse)
async def grant_project_access(
    access_data: UserProjectAccessCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Grant project access to a user.
    - senior_admin: Can grant access to any project
    - admin: Can grant access only to projects they have 'all' permission on
    """

    # Check if the current user has admin privileges
    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    # For non-senior admins, verify they can manage this specific project
    if current_user.role.name != "senior_admin":
        if not can_admin_manage_project(current_user, access_data.project_id, access_data.section, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only grant access to projects you have 'all' permission on"
            )

    # 2. Verify that the target user and project exist
    target_user = db.query(User).filter(User.id == access_data.user_id).first()
    if access_data.section == 1:
        project = db.query(Project).filter(Project.pid_po == access_data.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        valid_permissions = ["view", "edit", "all"]
        if access_data.permission_level not in valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level. Must be one of: {', '.join(valid_permissions)}"
            )

        # 4. Check if the user already has access
        existing_access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == access_data.user_id,
            UserProjectAccess.project_id == access_data.project_id
        ).first()

        if existing_access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has access to this project. Use update endpoint to modify permissions."
            )
        new_access = UserProjectAccess(
            user_id=access_data.user_id,
            project_id=access_data.project_id,
            permission_level=access_data.permission_level,
            Ranproject_id=None,
            Ropproject_id=None,
        )
    elif access_data.section == 2:
        ran_project = db.query(RanProject).filter(RanProject.pid_po == access_data.project_id).first()
        if not ran_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        valid_permissions = ["view", "edit", "all"]
        if access_data.permission_level not in valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level. Must be one of: {', '.join(valid_permissions)}"
            )

        # 4. Check if the user already has access
        existing_access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == access_data.user_id,
            UserProjectAccess.Ranproject_id == access_data.project_id
        ).first()

        if existing_access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has access to this project. Use update endpoint to modify permissions."
            )
        new_access = UserProjectAccess(
            user_id=access_data.user_id,
            project_id=None,
            permission_level=access_data.permission_level,
            Ranproject_id=access_data.project_id,
            Ropproject_id=None,
        )
    elif access_data.section == 3:
        rop_project = db.query(ROPProject).filter(ROPProject.pid_po == access_data.project_id).first()
        if not rop_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        valid_permissions = ["view", "edit", "all"]
        if access_data.permission_level not in valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level. Must be one of: {', '.join(valid_permissions)}"
            )

        # 4. Check if the user already has access
        existing_access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == access_data.user_id,
            UserProjectAccess.Ropproject_id == access_data.project_id
        ).first()

        if existing_access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has access to this project. Use update endpoint to modify permissions."
            )
        new_access = UserProjectAccess(
            user_id=access_data.user_id,
            project_id=None,
            permission_level=access_data.permission_level,
            Ropproject_id=access_data.project_id,
            Ranproject_id=None
        )
    elif access_data.section == 4:
        du_project = db.query(DUProject).filter(DUProject.pid_po == access_data.project_id).first()
        if not du_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DU Project not found"
            )
        valid_permissions = ["view", "edit", "all"]
        if access_data.permission_level not in valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level. Must be one of: {', '.join(valid_permissions)}"
            )

        # Check if the user already has access
        existing_access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == access_data.user_id,
            UserProjectAccess.DUproject_id == access_data.project_id
        ).first()

        if existing_access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has access to this project. Use update endpoint to modify permissions."
            )
        new_access = UserProjectAccess(
            user_id=access_data.user_id,
            project_id=None,
            permission_level=access_data.permission_level,
            Ranproject_id=None,
            Ropproject_id=None,
            DUproject_id=access_data.project_id
        )

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    db.add(new_access)
    db.commit()
    db.refresh(new_access)

    # 6. Create audit log
    try:
        # Determine which project variable to use based on section
        if access_data.section == 1:
            project_name = project.project_name
        elif access_data.section == 2:
            project_name = ran_project.project_name
        elif access_data.section == 3:
            project_name = rop_project.project_name
        elif access_data.section == 4:
            project_name = du_project.project_name
        else:
            project_name = "Unknown Project"

        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="grant_access",
            resource_type="project_access",
            resource_id=access_data.project_id,
            resource_name=project_name,
            details=json.dumps({
                "target_user": target_user.username,
                "permission_level": access_data.permission_level
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            project_id=access_data.project_id,
            section=access_data.section
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        # Continue without failing the main operation

    return new_access


@adminRoute.put("/update_project_access/{access_id}", response_model=UserProjectAccessResponse)
async def update_project_access(
    access_id: int,
    update_data: UserProjectAccessUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update project access permissions.
    - senior_admin: Can update any project access
    - admin: Can update only for projects they have 'all' permission on
    """

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    # Find the access record
    access_record = db.query(UserProjectAccess).filter(UserProjectAccess.id == access_id).first()
    if not access_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access record not found"
        )

    # For non-senior admins, verify they can manage this project
    if current_user.role.name != "senior_admin":
        # Determine section and project_id from the access record
        if access_record.project_id:
            section, project_id = 1, access_record.project_id
        elif access_record.Ranproject_id:
            section, project_id = 2, access_record.Ranproject_id
        elif access_record.Ropproject_id:
            section, project_id = 3, access_record.Ropproject_id
        elif access_record.DUproject_id:
            section, project_id = 4, access_record.DUproject_id
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid access record")

        if not can_admin_manage_project(current_user, project_id, section, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update access for projects you have 'all' permission on"
            )

    # Validate permission level
    valid_permissions = ["view", "edit", "all"]
    if update_data.permission_level not in valid_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission level. Must be one of: {', '.join(valid_permissions)}"
        )

    # Get related data for audit log
    user = db.query(User).filter(User.id == access_record.user_id).first()
    try:
        project = db.query(Project).filter(Project.pid_po == access_record.project_id).first()
    finally:
        pass
    try:
        ran_project = db.query(RanProject).filter(RanProject.pid_po == access_record.Ranproject_id).first()
    finally:
        pass
    try:
        rop_project = db.query(ROPProject).filter(ROPProject.pid_po == access_record.Ropproject_id).first()
    finally:
        pass
    try:
        du_project = db.query(DUProject).filter(DUProject.pid_po == access_record.DUproject_id).first()
    finally:
        pass

    old_permission = access_record.permission_level
    access_record.permission_level = update_data.permission_level

    db.commit()
    db.refresh(access_record)

    # Determine section and project_id for audit log
    if access_record.project_id:
        log_section, log_project_id = 1, access_record.project_id
    elif access_record.Ranproject_id:
        log_section, log_project_id = 2, access_record.Ranproject_id
    elif access_record.Ropproject_id:
        log_section, log_project_id = 3, access_record.Ropproject_id
    elif access_record.DUproject_id:
        log_section, log_project_id = 4, access_record.DUproject_id
    else:
        log_section, log_project_id = None, None

    # Create audit log
    try:
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_access",
            resource_type="project_access",
            resource_id=log_project_id,
            resource_name=project.project_name if project else ran_project.project_name if ran_project else rop_project.project_name if rop_project else du_project.project_name if du_project else "Unknown",
            details=json.dumps({
                "target_user": user.username if user else "Unknown",
                "old_permission": old_permission,
                "new_permission": update_data.permission_level
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            project_id=log_project_id,
            section=log_section
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

    return access_record


@adminRoute.delete("/revoke_project_access/{access_id}")
async def revoke_project_access(
    access_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke project access from a user.
    - senior_admin: Can revoke any project access
    - admin: Can revoke only for projects they have 'all' permission on
    """

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    # Find the access record
    access_record = db.query(UserProjectAccess).filter(UserProjectAccess.id == access_id).first()
    if not access_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access record not found"
        )

    # Determine section and project_id from the access record
    if access_record.project_id:
        section, project_id = 1, access_record.project_id
    elif access_record.Ranproject_id:
        section, project_id = 2, access_record.Ranproject_id
    elif access_record.Ropproject_id:
        section, project_id = 3, access_record.Ropproject_id
    elif access_record.DUproject_id:
        section, project_id = 4, access_record.DUproject_id
    else:
        section, project_id = None, None

    # For non-senior admins, verify they can manage this project
    if current_user.role.name != "senior_admin":
        if not project_id or not can_admin_manage_project(current_user, project_id, section, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only revoke access for projects you have 'all' permission on"
            )

    # Get related data for audit log before deletion
    user = db.query(User).filter(User.id == access_record.user_id).first()
    project = db.query(Project).filter(Project.pid_po == access_record.project_id).first()
    ran_project = db.query(RanProject).filter(RanProject.pid_po == access_record.Ranproject_id).first()
    rop_project = db.query(ROPProject).filter(ROPProject.pid_po == access_record.Ropproject_id).first()
    du_project = db.query(DUProject).filter(DUProject.pid_po == access_record.DUproject_id).first()

    # Store data before deletion
    deleted_permission = access_record.permission_level

    db.delete(access_record)
    db.commit()

    # Create audit log
    try:
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="revoke_access",
            resource_type="project_access",
            resource_id=project_id,
            resource_name=project.project_name if project else ran_project.project_name if ran_project else rop_project.project_name if rop_project else du_project.project_name if du_project else "Unknown",
            details=json.dumps({
                "target_user": user.username if user else "Unknown",
                "permission_level": deleted_permission
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            project_id=project_id,
            section=section
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

    return {"message": "Project access revoked successfully"}


# ===========================
# USER MANAGEMENT & VIEWING
# ===========================

@adminRoute.get("/users", response_model=List[UserWithProjectsResponse])
async def get_all_users_with_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get users with their project access.
    - senior_admin: Can see all users
    - admin: Can see only users who share at least one project with them
    """

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    # For non-senior admins, filter to users who share projects
    if current_user.role.name != "senior_admin":
        shared_user_ids = get_users_sharing_projects(current_user, db)
        users = db.query(User).join(Role).filter(User.id.in_(shared_user_ids)).all()
    else:
        # OPTIMIZED: Get all users with their roles
        users = db.query(User).join(Role).all()

    # For non-senior admins, get their accessible project IDs for filtering
    admin_accessible_projects = None
    if current_user.role.name != "senior_admin":
        admin_accessible_projects = get_all_user_accessible_project_ids(current_user, db)

    # OPTIMIZED: Fetch ALL UserProjectAccess records in one query
    all_accesses = db.query(UserProjectAccess).all()

    # OPTIMIZED: Group accesses by user_id for O(1) lookup
    accesses_by_user = {}
    for access in all_accesses:
        if access.user_id not in accesses_by_user:
            accesses_by_user[access.user_id] = []
        accesses_by_user[access.user_id].append(access)

    # OPTIMIZED: Collect all unique project IDs to batch fetch
    project_ids = set(a.project_id for a in all_accesses if a.project_id)
    ran_project_ids = set(a.Ranproject_id for a in all_accesses if a.Ranproject_id)
    rop_project_ids = set(a.Ropproject_id for a in all_accesses if a.Ropproject_id)
    du_project_ids = set(a.DUproject_id for a in all_accesses if a.DUproject_id)

    # OPTIMIZED: Batch fetch all projects in 4 queries instead of N*4 queries
    projects_map = {p.pid_po: p for p in db.query(Project).filter(Project.pid_po.in_(project_ids)).all()} if project_ids else {}
    ran_projects_map = {p.pid_po: p for p in db.query(RanProject).filter(RanProject.pid_po.in_(ran_project_ids)).all()} if ran_project_ids else {}
    rop_projects_map = {p.pid_po: p for p in db.query(ROPProject).filter(ROPProject.pid_po.in_(rop_project_ids)).all()} if rop_project_ids else {}
    du_projects_map = {p.pid_po: p for p in db.query(DUProject).filter(DUProject.pid_po.in_(du_project_ids)).all()} if du_project_ids else {}

    result = []
    for user in users:
        # OPTIMIZED: O(1) lookup instead of query
        user_accesses = accesses_by_user.get(user.id, [])

        projects = []
        for access in user_accesses:
            # OPTIMIZED: O(1) dictionary lookup instead of 4 queries per access
            project = projects_map.get(access.project_id)
            ran_project = ran_projects_map.get(access.Ranproject_id)
            rop_project = rop_projects_map.get(access.Ropproject_id)
            du_project = du_projects_map.get(access.DUproject_id)

            # For non-senior admins, only show projects they have access to
            if project:
                if admin_accessible_projects is None or access.project_id in admin_accessible_projects["boq"]:
                    projects.append({
                        "project_id": project.pid_po,
                        "project_name": project.project_name,
                        "permission_level": access.permission_level,
                        "access_id": access.id
                    })
            if ran_project:
                if admin_accessible_projects is None or access.Ranproject_id in admin_accessible_projects["ran"]:
                    projects.append({
                        "project_id": ran_project.pid_po,
                        "project_name": ran_project.project_name,
                        "permission_level": access.permission_level,
                        "access_id": access.id
                    })
            if rop_project:
                if admin_accessible_projects is None or access.Ropproject_id in admin_accessible_projects["rop"]:
                    projects.append({
                        "project_id": rop_project.pid_po,
                        "project_name": rop_project.project_name,
                        "permission_level": access.permission_level,
                        "access_id": access.id
                    })
            if du_project:
                if admin_accessible_projects is None or access.DUproject_id in admin_accessible_projects["du"]:
                    projects.append({
                        "project_id": du_project.pid_po,
                        "project_name": du_project.project_name,
                        "permission_level": access.permission_level,
                        "access_id": access.id
                    })
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role_name": user.role.name,
            "projects": projects,
            "can_access_approval": user.can_access_approval,
            "can_access_triggering": user.can_access_triggering,
            "can_access_logistics": user.can_access_logistics
        })

    return result


@adminRoute.get("/user/{user_id}/projects", response_model=UserWithProjectsResponse)
async def get_user_projects(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific user's project access.
    - senior_admin: Can see all projects for any user
    - admin: Can only see projects they share with the user
    """

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    # Get the user
    user = db.query(User).join(Role).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # For non-senior admins, verify they share at least one project with this user
    admin_accessible_projects = None
    if current_user.role.name != "senior_admin":
        shared_user_ids = get_users_sharing_projects(current_user, db)
        if user_id not in shared_user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view users who share projects with you"
            )
        admin_accessible_projects = get_all_user_accessible_project_ids(current_user, db)

    # OPTIMIZED: Get user's project access
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == user.id
    ).all()

    # OPTIMIZED: Collect unique project IDs from this user's accesses
    project_ids = set(a.project_id for a in user_accesses if a.project_id)
    ran_project_ids = set(a.Ranproject_id for a in user_accesses if a.Ranproject_id)
    rop_project_ids = set(a.Ropproject_id for a in user_accesses if a.Ropproject_id)
    du_project_ids = set(a.DUproject_id for a in user_accesses if a.DUproject_id)

    # OPTIMIZED: Batch fetch all projects in 4 queries instead of N*4 queries
    projects_map = {p.pid_po: p for p in db.query(Project).filter(Project.pid_po.in_(project_ids)).all()} if project_ids else {}
    ran_projects_map = {p.pid_po: p for p in db.query(RanProject).filter(RanProject.pid_po.in_(ran_project_ids)).all()} if ran_project_ids else {}
    rop_projects_map = {p.pid_po: p for p in db.query(ROPProject).filter(ROPProject.pid_po.in_(rop_project_ids)).all()} if rop_project_ids else {}
    du_projects_map = {p.pid_po: p for p in db.query(DUProject).filter(DUProject.pid_po.in_(du_project_ids)).all()} if du_project_ids else {}

    projects = []
    for access in user_accesses:
        # OPTIMIZED: O(1) dictionary lookup instead of 4 queries per access
        project = projects_map.get(access.project_id)
        ran_project = ran_projects_map.get(access.Ranproject_id)
        rop_project = rop_projects_map.get(access.Ropproject_id)
        du_project = du_projects_map.get(access.DUproject_id)

        # For non-senior admins, only show projects they have access to
        if project:
            if admin_accessible_projects is None or access.project_id in admin_accessible_projects["boq"]:
                projects.append({
                    "project_id": project.pid_po,
                    "project_name": project.project_name,
                    "permission_level": access.permission_level,
                    "access_id": access.id
                })
        if ran_project:
            if admin_accessible_projects is None or access.Ranproject_id in admin_accessible_projects["ran"]:
                projects.append({
                    "project_id": ran_project.pid_po,
                    "project_name": ran_project.project_name,
                    "permission_level": access.permission_level,
                    "access_id": access.id
                })
        if rop_project:
            if admin_accessible_projects is None or access.Ropproject_id in admin_accessible_projects["rop"]:
                projects.append({
                    "project_id": rop_project.pid_po,
                    "project_name": rop_project.project_name,
                    "permission_level": access.permission_level,
                    "access_id": access.id
                })
        if du_project:
            if admin_accessible_projects is None or access.DUproject_id in admin_accessible_projects["du"]:
                projects.append({
                    "project_id": du_project.pid_po,
                    "project_name": du_project.project_name,
                    "permission_level": access.permission_level,
                    "access_id": access.id
                })

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role_name": user.role.name,
        "projects": projects,
        "can_access_approval": user.can_access_approval,
        "can_access_triggering": user.can_access_triggering,
        "can_access_logistics": user.can_access_logistics
    }


# ===========================
# AUDIT LOG MANAGEMENT
# ===========================

@adminRoute.get("", response_model=PaginatedAuditLogResponse)
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit logs with pagination.
    - senior_admin: Can see all logs
    - admin: Can see logs related to projects they have access to, plus their own actions

    OPTIMIZED: Returns total count for proper pagination + server-side search filtering.
    """

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view audit logs"
        )

    try:
        # Build query with eager loading to prevent N+1
        query = db.query(AuditLog).join(User).join(Role)

        # For non-senior admins, filter to show only:
        # 1. Logs for projects they have access to
        # 2. Their own actions (login, logout, etc.)
        # 3. Actions by users who share projects with them
        if current_user.role.name != "senior_admin":
            accessible_projects = get_all_accessible_project_ids_flat(current_user, db)
            shared_user_ids = get_users_sharing_projects(current_user, db)

            # Build filter: logs with matching project_id OR logs from shared users OR own logs
            project_filter = []
            if accessible_projects:
                project_filter.append(AuditLog.project_id.in_(accessible_projects))

            query = query.filter(
                or_(
                    AuditLog.user_id == current_user.id,  # Own actions
                    AuditLog.user_id.in_(shared_user_ids),  # Actions by users sharing projects
                    *project_filter  # Project-specific logs
                )
            )

        # Apply additional filters
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        # OPTIMIZED: Server-side search filtering
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_term),
                    AuditLog.action.ilike(search_term),
                    AuditLog.resource_name.ilike(search_term),
                    AuditLog.resource_type.ilike(search_term)
                )
            )

        # OPTIMIZED: Get total count before pagination
        total_count = query.count()

        # Order by timestamp descending (newest first) and apply pagination
        audit_logs = query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit).all()

        # Format response
        result = []
        for log in audit_logs:
            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "resource_name": log.resource_name,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp,
                "user": {
                    "id": log.user.id,
                    "username": log.user.username,
                    "email": log.user.email,
                    "role": log.user.role.name
                }
            })

        # OPTIMIZED: Return paginated response with total count
        return {
            "records": result,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        # Return empty paginated response if there's an error
        return {
            "records": [],
            "total": 0,
            "skip": skip,
            "limit": limit
        }


@adminRoute.get("/actions")
async def get_available_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available actions for filtering. Admins can access this."""

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    try:
        # Get distinct actions from audit logs
        actions = db.query(AuditLog.action).distinct().all()
        return {"actions": [action[0] for action in actions if action[0]]}
    except Exception as e:
        logger.error(f"Error fetching actions: {e}")
        return {"actions": []}


@adminRoute.get("/resource_types")
async def get_available_resource_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available resource types for filtering. Admins can access this."""

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    try:
        # Get distinct resource types from audit logs
        resource_types = db.query(AuditLog.resource_type).distinct().all()
        return {"resource_types": [rt[0] for rt in resource_types if rt[0]]}
    except Exception as e:
        logger.error(f"Error fetching resource types: {e}")
        return {"resource_types": []}


@adminRoute.get("/roles")
async def get_all_roles(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all available roles. Admins can access this."""

    if current_user.role.name not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    try:
        roles = db.query(Role).all()
        return {"roles": [{"id": role.id, "name": role.name} for role in roles]}
    except Exception as e:
        logger.error(f"Error fetching roles: {e}")
        return {"roles": []}


@adminRoute.put("/update_user_role", response_model=UserRoleUpdateResponse)
async def update_user_role(
        role_data: UserRoleUpdateRequest,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update user role. Only senior_admin can do this."""

    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    # Find the target user
    target_user = db.query(User).filter(User.id == role_data.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Find the new role
    new_role = db.query(Role).filter(Role.name == role_data.new_role_name).first()
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Prevent changing own role
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role"
        )

    # Store old role for audit log
    old_role_name = target_user.role.name

    # Update the user's role
    target_user.role_id = new_role.id
    db.commit()
    db.refresh(target_user)

    # Create audit log
    try:
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_user_role",
            resource_type="user",
            resource_id=str(target_user.id),
            resource_name=target_user.username,
            details=json.dumps({
                "target_user": target_user.username,
                "old_role": old_role_name,
                "new_role": role_data.new_role_name
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

    return UserRoleUpdateResponse(
        id=target_user.id,
        username=target_user.username,
        email=target_user.email,
        old_role=old_role_name,
        new_role=role_data.new_role_name
    )


# ===========================
# APPROVAL STAGE ACCESS MANAGEMENT
# ===========================

@adminRoute.put("/update_approval_stage_access", response_model=ApprovalStageAccessResponse)
async def update_approval_stage_access(
    access_data: ApprovalStageAccessUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update approval workflow stage access for a user. Only senior_admin can do this."""

    # Check if the current user has the 'senior_admin' role
    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    # Find the target user
    target_user = db.query(User).filter(User.id == access_data.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update stage access permissions
    if access_data.can_access_approval is not None:
        target_user.can_access_approval = access_data.can_access_approval
    if access_data.can_access_triggering is not None:
        target_user.can_access_triggering = access_data.can_access_triggering
    if access_data.can_access_logistics is not None:
        target_user.can_access_logistics = access_data.can_access_logistics

    db.commit()
    db.refresh(target_user)

    # Create audit log
    try:
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_approval_stage_access",
            resource_type="user",
            resource_id=str(target_user.id),
            resource_name=target_user.username,
            details=json.dumps({
                "target_user": target_user.username,
                "can_access_approval": target_user.can_access_approval,
                "can_access_triggering": target_user.can_access_triggering,
                "can_access_logistics": target_user.can_access_logistics
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

    return ApprovalStageAccessResponse(
        id=target_user.id,
        username=target_user.username,
        can_access_approval=target_user.can_access_approval,
        can_access_triggering=target_user.can_access_triggering,
        can_access_logistics=target_user.can_access_logistics
    )