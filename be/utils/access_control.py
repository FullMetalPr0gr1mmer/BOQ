"""
Access Control Utilities

Centralized access control and permission checking functions.
Eliminates duplication across route files.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, Request, status

from Models.Admin.User import User, UserProjectAccess
from Models.BOQ.Project import Project


def check_project_access(
    current_user: User,
    project: Project,
    db: Session,
    required_permission: str = "view"
) -> bool:
    """
    Helper function to check if a user has access to a project with the required permission level.

    Args:
        current_user: The current user
        project: The project to check access for
        db: Database session
        required_permission: Required permission level ("view", "edit", or "all")

    Returns:
        bool: True if user has required permission, False otherwise
    """
    if not project:
        return False  # No project, no access

    # Senior admins have access to everything
    if current_user.role.name == "senior_admin":
        return True

    # Check user's project access
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == project.pid_po
    ).first()

    if not access:
        return False

    # Define permission hierarchy
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_projects(current_user: User, db: Session) -> List[Project]:
    """
    Get all projects that the current user has access to.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        List[Project]: List of accessible projects
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return db.query(Project).all()

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.project_id for access in user_accesses]

    # Return projects that match those IDs
    return db.query(Project).filter(Project.pid_po.in_(accessible_project_ids)).all()


def get_user_accessible_project_ids(current_user: User, db: Session) -> List[str]:
    """
    Get list of project IDs (pid_po) that the current user has access to.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        List[str]: List of accessible project IDs
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return [p.pid_po for p in db.query(Project.pid_po).all()]

    # For other users, get project IDs they have access to
    return [
        access.project_id for access in db.query(UserProjectAccess.project_id).filter(
            UserProjectAccess.user_id == current_user.id
        ).all()
    ]


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Args:
        request: FastAPI Request object

    Returns:
        str: Client IP address
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def require_project_access(
    current_user: User,
    project: Optional[Project],
    db: Session,
    required_permission: str = "view",
    error_message: Optional[str] = None
) -> None:
    """
    Check project access and raise HTTPException if not authorized.
    Convenience function that combines check with error handling.

    Args:
        current_user: The current user
        project: The project to check access for
        db: Database session
        required_permission: Required permission level
        error_message: Custom error message (optional)

    Raises:
        HTTPException: If user doesn't have required permission
    """
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not check_project_access(current_user, project, db, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message or f"You are not authorized to {required_permission} this project."
        )
