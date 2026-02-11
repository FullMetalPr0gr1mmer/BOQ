"""
Access Control Utilities

Centralized access control and permission checking functions.
Eliminates duplication across route files.
"""

from typing import List, Optional, Set, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, Request, status

from Models.Admin.User import User, UserProjectAccess
from Models.BOQ.Project import Project
from Models.RAN.RANProject import RanProject
from Models.LE.ROPProject import ROPProject
import importlib
du_project_module = importlib.import_module("Models.DU.DU_Project")
DUProject = du_project_module.DUProject


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


def get_all_user_accessible_project_ids(current_user: User, db: Session) -> Dict[str, Set[str]]:
    """
    Get all project IDs the user has access to across all project types.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        Dict with keys 'boq', 'ran', 'rop', 'du' containing sets of project IDs
    """
    result = {
        "boq": set(),
        "ran": set(),
        "rop": set(),
        "du": set()
    }

    # Senior admin has access to all projects
    if current_user.role.name == "senior_admin":
        result["boq"] = {p.pid_po for p in db.query(Project.pid_po).all()}
        result["ran"] = {p.pid_po for p in db.query(RanProject.pid_po).all()}
        result["rop"] = {p.pid_po for p in db.query(ROPProject.pid_po).all()}
        result["du"] = {p.pid_po for p in db.query(DUProject.pid_po).all()}
        return result

    # Get user's project access records
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    for access in user_accesses:
        if access.project_id:
            result["boq"].add(access.project_id)
        if access.Ranproject_id:
            result["ran"].add(access.Ranproject_id)
        if access.Ropproject_id:
            result["rop"].add(access.Ropproject_id)
        if access.DUproject_id:
            result["du"].add(access.DUproject_id)

    return result


def get_all_accessible_project_ids_flat(current_user: User, db: Session) -> Set[str]:
    """
    Get a flat set of all project IDs the user has access to (all types combined).

    Args:
        current_user: The current user
        db: Database session

    Returns:
        Set[str]: Combined set of all accessible project IDs
    """
    projects_by_type = get_all_user_accessible_project_ids(current_user, db)
    return projects_by_type["boq"] | projects_by_type["ran"] | projects_by_type["rop"] | projects_by_type["du"]


def get_users_sharing_projects(current_user: User, db: Session) -> Set[int]:
    """
    Get all user IDs that share at least one project with the current user.

    OPTIMIZED: Uses database-level filtering instead of loading all records into memory.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        Set[int]: User IDs that share projects with current user
    """
    from sqlalchemy import or_

    if current_user.role.name == "senior_admin":
        return {u.id for u in db.query(User.id).all()}

    # Get current user's accessible project IDs
    accessible_projects = get_all_user_accessible_project_ids(current_user, db)

    # Build filter conditions for each project type
    conditions = []

    if accessible_projects["boq"]:
        conditions.append(UserProjectAccess.project_id.in_(accessible_projects["boq"]))
    if accessible_projects["ran"]:
        conditions.append(UserProjectAccess.Ranproject_id.in_(accessible_projects["ran"]))
    if accessible_projects["rop"]:
        conditions.append(UserProjectAccess.Ropproject_id.in_(accessible_projects["rop"]))
    if accessible_projects["du"]:
        conditions.append(UserProjectAccess.DUproject_id.in_(accessible_projects["du"]))

    # If user has no project access, return only their own ID
    if not conditions:
        return {current_user.id}

    # OPTIMIZED: Query only user_ids matching the project filters at database level
    shared_user_ids = {
        access.user_id for access in db.query(UserProjectAccess.user_id).filter(
            or_(*conditions)
        ).distinct().all()
    }

    # Always include self
    shared_user_ids.add(current_user.id)

    return shared_user_ids


def can_admin_manage_project(current_user: User, project_id: str, section: int, db: Session) -> bool:
    """
    Check if an admin can manage (grant/revoke access) for a specific project.

    Args:
        current_user: The current user
        project_id: The project ID (pid_po)
        section: Project section (1=BOQ, 2=RAN, 3=ROP, 4=DU)
        db: Database session

    Returns:
        bool: True if user can manage this project
    """
    if current_user.role.name == "senior_admin":
        return True

    if current_user.role.name != "admin":
        return False

    # Check if admin has "all" permission on this project
    accessible_projects = get_all_user_accessible_project_ids(current_user, db)

    section_map = {1: "boq", 2: "ran", 3: "rop", 4: "du"}
    project_type = section_map.get(section)

    if not project_type or project_id not in accessible_projects[project_type]:
        return False

    # Check permission level - admin needs "all" permission to manage
    if section == 1:
        access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == current_user.id,
            UserProjectAccess.project_id == project_id
        ).first()
    elif section == 2:
        access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == current_user.id,
            UserProjectAccess.Ranproject_id == project_id
        ).first()
    elif section == 3:
        access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == current_user.id,
            UserProjectAccess.Ropproject_id == project_id
        ).first()
    elif section == 4:
        access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == current_user.id,
            UserProjectAccess.DUproject_id == project_id
        ).first()
    else:
        return False

    return access and access.permission_level == "all"
