# routes/adminRoute.py
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session
from APIs.Core import get_current_user, get_db
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
    UserWithProjectsResponse
)
from Schemas.Admin.LogSchema import AuditLogResponse
from Schemas.Admin.UserSchema import UserRoleUpdateResponse, UserRoleUpdateRequest

adminRoute = APIRouter(prefix="/audit-logs",tags=["Admin"])

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
    user_agent: Optional[str] = None
):
    """Create an audit log entry."""
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
    """Grant project access to a user. Only senior_admin can do this."""

    # 1. Check if the current user has the 'senior_admin' role
    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
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
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="grant_access",
            resource_type="project_access",
            resource_id=access_data.project_id,
            resource_name=project.project_name,
            details=json.dumps({
                "target_user": target_user.username,
                "permission_level": access_data.permission_level
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
    except Exception as e:
        print(f"Failed to create audit log: {e}")
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
    """Update project access permissions. Only senior_admin can do this."""

    if current_user.role.name != "senior_admin":
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

    # Create audit log
    try:
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_access",
            resource_type="project_access",
            resource_id=access_record.project_id,
            resource_name=project.project_name if project else ran_project.project_name if ran_project else rop_project.project_name if rop_project else du_project.project_name if du_project else "Unknown",
            details=json.dumps({
                "target_user": user.username if user else "Unknown",
                "old_permission": old_permission,
                "new_permission": update_data.permission_level
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
    except Exception as e:
        print(f"Failed to create audit log: {e}")

    return access_record


@adminRoute.delete("/revoke_project_access/{access_id}")
async def revoke_project_access(
    access_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke project access from a user. Only senior_admin can do this."""

    if current_user.role.name != "senior_admin":
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

    # Get related data for audit log before deletion
    user = db.query(User).filter(User.id == access_record.user_id).first()
    project = db.query(Project).filter(Project.pid_po == access_record.project_id).first()
    ran_project = db.query(RanProject).filter(RanProject.pid_po == access_record.Ranproject_id).first()
    rop_project = db.query(ROPProject).filter(ROPProject.pid_po == access_record.Ropproject_id).first()
    du_project = db.query(DUProject).filter(DUProject.pid_po == access_record.DUproject_id).first()

    # Store data before deletion
    deleted_project_id = access_record.project_id
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
            resource_id=deleted_project_id,
            resource_name=project.project_name if project else ran_project.project_name if ran_project else rop_project.project_name if rop_project else du_project.project_name if du_project else "Unknown",
            details=json.dumps({
                "target_user": user.username if user else "Unknown",
                "permission_level": deleted_permission
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
    except Exception as e:
        print(f"Failed to create audit log: {e}")

    return {"message": "Project access revoked successfully"}


# ===========================
# USER MANAGEMENT & VIEWING
# ===========================

@adminRoute.get("/users", response_model=List[UserWithProjectsResponse])
async def get_all_users_with_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users with their project access. Only senior_admin can access this."""

    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    # Get all users with their roles
    users = db.query(User).join(Role).all()

    result = []
    for user in users:
        # Get user's project access
        user_accesses = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == user.id
        ).all()



        projects = []
        for access in user_accesses:
            project = db.query(Project).filter(Project.pid_po == access.project_id).first()
            ran_project= db.query(RanProject).filter(RanProject.pid_po == access.Ranproject_id).first()
            rop_project= db.query(ROPProject).filter(ROPProject.pid_po == access.Ropproject_id).first()
            du_project = db.query(DUProject).filter(DUProject.pid_po == access.DUproject_id).first()

            if project:
                projects.append({
                    "project_id": project.pid_po,
                    "project_name": project.project_name,
                    "permission_level": access.permission_level,
                    "access_id": access.id
                })
            if ran_project:
                projects.append({
                    "project_id": ran_project.pid_po,
                    "project_name": ran_project.project_name,
                    "permission_level": access.permission_level,
                    "access_id": access.id
                })
            if rop_project:
                projects.append({
                    "project_id": rop_project.pid_po,
                    "project_name": rop_project.project_name,
                    "permission_level": access.permission_level,
                    "access_id": access.id
                })
            if du_project:
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
            "projects": projects
        })

    return result


@adminRoute.get("/user/{user_id}/projects", response_model=UserWithProjectsResponse)
async def get_user_projects(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific user's project access. Only senior_admin can access this."""

    if current_user.role.name != "senior_admin":
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

    # Get user's project access
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == user.id
    ).all()

    projects = []
    for access in user_accesses:
        project = db.query(Project).filter(Project.pid_po == access.project_id).first()
        ran_project = db.query(RanProject).filter(RanProject.pid_po == access.Ranproject_id).first()
        rop_project = db.query(ROPProject).filter(ROPProject.pid_po == access.Ropproject_id).first()
        du_project = db.query(DUProject).filter(DUProject.pid_po == access.DUproject_id).first()

        if project:
            projects.append({
                "project_id": project.pid_po,
                "project_name": project.project_name,
                "permission_level": access.permission_level,
                "access_id": access.id
            })
        if ran_project:
            projects.append({
                "project_id": ran_project.pid_po,
                "project_name": ran_project.project_name,
                "permission_level": access.permission_level,
                "access_id": access.id
            })
        if rop_project:
            projects.append({
                "project_id": rop_project.pid_po,
                "project_name": rop_project.project_name,
                "permission_level": access.permission_level,
                "access_id": access.id
            })
        if du_project:
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
        "projects": projects
    }


# ===========================
# AUDIT LOG MANAGEMENT
# ===========================

@adminRoute.get("", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit logs. Only senior_admin can access this."""

    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view audit logs"
        )

    try:
        # Build query
        query = db.query(AuditLog).join(User)

        # Apply filters
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        # Order by timestamp descending (newest first)
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

        return result

    except Exception as e:
        print(f"Error fetching audit logs: {e}")
        # Return empty list if there's an error
        return []


@adminRoute.get("/actions")
async def get_available_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available actions for filtering. Only senior_admin can access this."""

    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    try:
        # Get distinct actions from audit logs
        actions = db.query(AuditLog.action).distinct().all()
        return {"actions": [action[0] for action in actions if action[0]]}
    except Exception as e:
        print(f"Error fetching actions: {e}")
        return {"actions": []}


@adminRoute.get("/resource_types")
async def get_available_resource_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available resource types for filtering. Only senior_admin can access this."""

    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    try:
        # Get distinct resource types from audit logs
        resource_types = db.query(AuditLog.resource_type).distinct().all()
        return {"resource_types": [rt[0] for rt in resource_types if rt[0]]}
    except Exception as e:
        print(f"Error fetching resource types: {e}")
        return {"resource_types": []}


@adminRoute.get("/roles")
async def get_all_roles(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all available roles. Only senior_admin can access this."""

    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information"
        )

    try:
        roles = db.query(Role).all()
        return {"roles": [{"id": role.id, "name": role.name} for role in roles]}
    except Exception as e:
        print(f"Error fetching roles: {e}")
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
        print(f"Failed to create audit log: {e}")

    return UserRoleUpdateResponse(
        id=target_user.id,
        username=target_user.username,
        email=target_user.email,
        old_role=old_role_name,
        new_role=role_data.new_role_name
    )