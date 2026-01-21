# routes/DU_ProjectRoute.py
"""
DU Project API Routes

This module provides CRUD operations for managing DU (Digital Transformation) Projects.
It includes pagination, search, admin control, and cascading PO updates.
"""

import logging
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import and_
from sqlalchemy.orm import Session

from APIs.Core import get_db, get_current_user
from Models.Admin.User import UserProjectAccess, User
from Models.Admin.AuditLog import AuditLog

# Configure logging
logger = logging.getLogger(__name__)

# Import model using importlib since we need to reference it dynamically
import importlib
du_project_model = importlib.import_module("Models.DU.DU_Project")
DUProject = du_project_model.DUProject

# Import the 5G Rollout Sheet model for cascading updates
rollout_model = importlib.import_module("Models.DU.5G_Rollout_Sheet")
_5G_Rollout_Sheet = rollout_model._5G_Rollout_Sheet

# Import schemas
du_schema = importlib.import_module("Schemas.DU.DU_ProjectSchema")
CreateDUProject = du_schema.CreateDUProject
UpdateDUProject = du_schema.UpdateDUProject
DUProjectOut = du_schema.DUProjectOut
DUProjectPagination = du_schema.DUProjectPagination
UpdatePOSchema = du_schema.UpdatePOSchema
UpdatePOResponse = du_schema.UpdatePOResponse
DUProjectPermission = du_schema.DUProjectPermission

DUProjectRoute = APIRouter(prefix="/du-projects", tags=["DU Projects"])


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


def check_du_project_access(current_user: User, project: DUProject, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a DU project with required permission level.

    Args:
        current_user: The current user
        project: The DU project to check access for
        db: Database session
        required_permission: Required permission level ("view", "edit", "all")

    Returns:
        bool: True if user has access, False otherwise
    """
    # Senior admin has all permissions to all projects
    if current_user.role.name == "senior_admin":
        return True

    # Admin has all permissions but only to projects they have access to
    # Check UserProjectAccess for both admin and other roles
    access = db.query(UserProjectAccess).filter(and_(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.DUproject_id == project.pid_po
    )).first()

    if not access:
        return False

    # Admin with any access level gets full permissions (same as senior_admin) for their projects
    if current_user.role.name == "admin":
        return True

    # For non-admin users, check permission levels
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_du_projects(current_user: User, db: Session) -> List[DUProjectOut]:
    """
    Get all DU projects that the current user has access to.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        List[DUProject]: List of accessible DU projects
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return db.query(DUProject).all()

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.DUproject_id for access in user_accesses if access.DUproject_id]

    if not accessible_project_ids:
        return []

    # Return projects that match those IDs
    return db.query(DUProject).filter(DUProject.pid_po.in_(accessible_project_ids)).all()


# ===========================
# CRUD OPERATIONS
# ===========================

@DUProjectRoute.post("", response_model=DUProjectOut)
async def add_du_project(
        project_data: CreateDUProject,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new DU project. Only senior_admin can create projects.
    """
    logger.info(f"User {current_user.username} attempting to create DU project: {project_data.pid + project_data.po}")

    # Only senior_admin can create projects
    if current_user.role.name != "senior_admin":
        logger.warning(f"User {current_user.username} (role: {current_user.role.name}) denied permission to create DU project")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action. Contact the Senior Admin."
        )

    pid_po = project_data.pid + project_data.po
    existing_project = db.query(DUProject).filter(DUProject.pid_po == pid_po).first()
    if existing_project:
        logger.warning(f"Attempt to create duplicate DU project: {pid_po}")
        raise HTTPException(status_code=400, detail="DU Project already exists")

    try:
        new_project_db = DUProject(
            pid_po=pid_po,
            project_name=project_data.project_name,
            pid=project_data.pid,
            po=project_data.po
        )
        db.add(new_project_db)
        db.commit()
        db.refresh(new_project_db)
        logger.info(f"DU project created successfully: {pid_po} by user {current_user.username}")

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_du_project",
            resource_type="du_project",
            resource_id=pid_po,
            resource_name=project_data.project_name,
            details=json.dumps({
                "pid": project_data.pid,
                "po": project_data.po
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return new_project_db
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating DU project {pid_po}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating DU project: {str(e)}"
        )


@DUProjectRoute.get("", response_model=DUProjectPagination)
def get_du_projects(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=10000),
        search: str = Query(""),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all DU projects accessible to the current user with pagination.
    - senior_admin: Can see all projects
    - admin: Can see only projects they have access to
    - user: Can see only projects they have access to

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        search: Search term to filter by project name, pid, or po
    """
    logger.info(f"User {current_user.username} (ID: {current_user.id}) requesting DU projects - skip: {skip}, limit: {limit}, search: '{search}'")

    try:
        accessible_projects = get_user_accessible_du_projects(current_user, db)
        logger.debug(f"User {current_user.username} has access to {len(accessible_projects)} DU projects")

        # Apply search filter if provided
        if search.strip():
            search_lower = search.strip().lower()
            accessible_projects = [
                p for p in accessible_projects
                if (search_lower in (p.project_name or "").lower() or
                    search_lower in (p.pid or "").lower() or
                    search_lower in (p.po or "").lower() or
                    search_lower in (p.pid_po or "").lower())
            ]
            logger.debug(f"After search filter: {len(accessible_projects)} projects match")

        total = len(accessible_projects)

        # Apply pagination
        paginated_projects = accessible_projects[skip:skip + limit]

        logger.info(f"Returning {len(paginated_projects)} DU projects out of {total} total for user {current_user.username}")
        return DUProjectPagination(records=paginated_projects, total=total)
    except Exception as e:
        logger.error(f"Error retrieving DU projects for user {current_user.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving DU projects: {str(e)}"
        )


@DUProjectRoute.get("/check-permission/{pid_po}", response_model=DUProjectPermission)
def check_user_du_project_permission(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Check what permissions the current user has for a specific DU project.
    Returns the permission level and available actions.
    Must be defined before /{pid_po} to avoid route conflict.
    """
    project = db.query(DUProject).filter(DUProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="DU Project not found")

    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return DUProjectPermission(
            project_id=pid_po,
            permission_level="all",
            can_view=True,
            can_edit=True,
            can_delete=True,
            role="senior_admin"
        )

    # Check access for other users
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.DUproject_id == project.pid_po
    ).first()

    if not access:
        return DUProjectPermission(
            project_id=pid_po,
            permission_level="none",
            can_view=False,
            can_edit=False,
            can_delete=False,
            role=current_user.role.name
        )

    # Determine capabilities based on permission level and role
    can_edit = (current_user.role.name == "admin" and
                access.permission_level in ["edit", "all"])
    can_delete = (current_user.role.name == "admin" and
                  access.permission_level == "all")

    return DUProjectPermission(
        project_id=pid_po,
        permission_level=access.permission_level,
        can_view=True,
        can_edit=can_edit,
        can_delete=can_delete,
        role=current_user.role.name
    )


@DUProjectRoute.get("/{pid_po}", response_model=DUProjectOut)
def get_du_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific DU project by pid_po.
    Users can only access projects they have permission for.
    """
    project = db.query(DUProject).filter(DUProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="DU Project not found")

    # Check if user has access to this project
    if not check_du_project_access(current_user, project, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this DU project. Contact the Senior Admin."
        )

    return project


@DUProjectRoute.put("/{pid_po}", response_model=DUProjectOut)
async def update_du_project(
        pid_po: str,
        update_data: UpdateDUProject,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update a DU project.
    - senior_admin: Can update any project
    - Users with "edit" or "all" permission: Can update projects they have access to
    """
    project = db.query(DUProject).filter(DUProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="DU Project not found")

    # Check if user has edit permission
    if not check_du_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this DU project. Contact the Senior Admin."
        )

    # Update the project
    try:
        old_name = project.project_name
        if update_data.project_name:
            project.project_name = update_data.project_name

        db.commit()
        db.refresh(project)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_du_project",
            resource_type="du_project",
            resource_id=pid_po,
            resource_name=project.project_name,
            details=json.dumps({
                "old_name": old_name,
                "new_name": update_data.project_name
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return project
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating DU project: {str(e)}"
        )


@DUProjectRoute.delete("/{pid_po}")
async def delete_du_project(
        pid_po: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a DU project.
    - senior_admin: Can delete any project
    - Users with "all" permission: Can delete projects they have full access to

    Note: This will also delete all related 5G Rollout Sheet entries.
    """
    logger.info(f"User {current_user.username} attempting to delete DU project: {pid_po}")

    project = db.query(DUProject).filter(DUProject.pid_po == pid_po).first()
    if not project:
        logger.warning(f"Attempt to delete non-existent DU project: {pid_po}")
        raise HTTPException(status_code=404, detail="DU Project not found")

    # Check if user has "all" permission (required for deletion)
    if not check_du_project_access(current_user, project, db, "all"):
        logger.warning(f"User {current_user.username} denied permission to delete DU project: {pid_po}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this DU project. Contact the Senior Admin."
        )

    # Delete the project and related data
    try:
        project_name = project.project_name

        # Count related records for response
        rollout_count = db.query(_5G_Rollout_Sheet).filter(
            _5G_Rollout_Sheet.project_id == pid_po
        ).count()

        logger.info(f"Deleting DU project {pid_po} with {rollout_count} related rollout sheet entries")

        # Delete related 5G Rollout Sheet entries first
        db.query(_5G_Rollout_Sheet).filter(
            _5G_Rollout_Sheet.project_id == pid_po
        ).delete(synchronize_session=False)

        # Delete the project
        db.delete(project)
        db.commit()

        logger.info(f"DU project {pid_po} deleted successfully by user {current_user.username}")

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_du_project",
            resource_type="du_project",
            resource_id=pid_po,
            resource_name=project_name,
            details=json.dumps({
                "deleted_rollout_sheets": rollout_count
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": f"DU Project '{pid_po}' deleted successfully",
            "deleted_rollout_sheets": rollout_count
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting DU project {pid_po}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting DU project: {str(e)}"
        )


@DUProjectRoute.put("/{old_pid_po}/update-po", response_model=UpdatePOResponse)
async def update_project_purchase_order(
        old_pid_po: str,
        update_data: UpdatePOSchema,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update the Purchase Order (PO) for a DU project with cascading updates.
    This will update the pid_po across all related tables.

    CAUTION: This is a destructive operation - the old pid_po will no longer exist.
    Only senior_admin can perform this operation.

    Args:
        old_pid_po: Current project identifier (pid + po)
        update_data: New PO value

    Returns:
        UpdatePOResponse with details of all updated records
    """
    # Only senior_admin can execute this operation
    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Senior Admin can update project purchase orders. This is a destructive operation."
        )

    # Validate the old project exists
    project = db.query(DUProject).filter(DUProject.pid_po == old_pid_po).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DU Project with pid_po '{old_pid_po}' not found"
        )

    # Validate new PO is not empty
    new_po = update_data.new_po.strip()
    if not new_po:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New purchase order cannot be empty"
        )

    # Calculate new pid_po
    new_pid_po = project.pid + new_po

    # Check that new pid_po doesn't already exist
    existing_project = db.query(DUProject).filter(DUProject.pid_po == new_pid_po).first()
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A project with pid_po '{new_pid_po}' already exists. Cannot proceed with update."
        )

    try:
        # Track affected records - count them first before any updates
        affected_tables = {}

        # Count 5G Rollout Sheet records
        rollout_count = db.query(_5G_Rollout_Sheet).filter(
            _5G_Rollout_Sheet.project_id == old_pid_po
        ).count()

        # Count UserProjectAccess records
        user_access_count = db.query(UserProjectAccess).filter(
            UserProjectAccess.DUproject_id == old_pid_po
        ).count()

        # STEP 1: Update the project itself FIRST (create the new primary key)
        # Add a new project with the new pid_po
        new_project = DUProject(
            pid_po=new_pid_po,
            pid=project.pid,
            po=new_po,
            project_name=project.project_name
        )
        db.add(new_project)
        db.flush()  # Make the new project available for foreign key references

        # STEP 2: Now update all foreign key references to point to the new pid_po
        # Update 5G Rollout Sheet records
        db.query(_5G_Rollout_Sheet).filter(
            _5G_Rollout_Sheet.project_id == old_pid_po
        ).update({"project_id": new_pid_po}, synchronize_session=False)
        affected_tables["5g_rollout_sheet"] = rollout_count

        # Update UserProjectAccess records
        db.query(UserProjectAccess).filter(
            UserProjectAccess.DUproject_id == old_pid_po
        ).update({"DUproject_id": new_pid_po}, synchronize_session=False)
        affected_tables["user_project_access"] = user_access_count

        # STEP 3: Delete the old project record (now that all foreign keys point to new one)
        db.delete(project)

        # Commit all changes atomically
        db.commit()
        db.refresh(new_project)

        # Calculate total records updated
        total_records_updated = sum(affected_tables.values())

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_du_project_po",
            resource_type="du_project",
            resource_id=new_pid_po,
            resource_name=project.project_name,
            details=json.dumps({
                "old_pid_po": old_pid_po,
                "new_pid_po": new_pid_po,
                "old_po": project.po,
                "new_po": new_po,
                "affected_tables": affected_tables,
                "total_records_updated": total_records_updated
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return UpdatePOResponse(
            old_pid_po=old_pid_po,
            new_pid_po=new_pid_po,
            affected_tables=affected_tables,
            total_records_updated=total_records_updated,
            message=f"Successfully updated purchase order from '{old_pid_po}' to '{new_pid_po}'. Total {total_records_updated} related records updated across {len(affected_tables)} tables."
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating purchase order: {str(e)}"
        )


# ===========================
# STATISTICS ENDPOINT
# ===========================

@DUProjectRoute.get("/stats/summary")
def get_du_projects_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get statistics summary for DU projects accessible to the current user.
    """
    try:
        accessible_projects = get_user_accessible_du_projects(current_user, db)

        total_projects = len(accessible_projects)

        # Count total rollout sheet entries for accessible projects
        if accessible_projects:
            project_ids = [p.pid_po for p in accessible_projects]
            total_rollout_entries = db.query(_5G_Rollout_Sheet).filter(
                _5G_Rollout_Sheet.project_id.in_(project_ids)
            ).count()
        else:
            total_rollout_entries = 0

        return {
            "total_projects": total_projects,
            "total_rollout_entries": total_rollout_entries
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving DU project stats: {str(e)}"
        )
