from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from APIs.Core import get_db, get_current_user
from Models.Admin.User import UserProjectAccess, User
from Models.RAN import RANProject
from Models.RAN.RANProject import RanProject
from Schemas.RAN.RANProjectSchema import CreateRANProject, UpdateRANProject, RANProjectOUT

RANProjectRoute = APIRouter(prefix="/ran-projects", tags=["RANProjects"])


def check_ran_project_access(current_user: User, project: RANProject, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a RAN project with required permission level.

    Args:
        current_user: The current user
        project: The RAN project to check access for
        db: Database session
        required_permission: Required permission level ("view", "edit", "all")

    Returns:
        bool: True if user has access, False otherwise
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(and_(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ranproject_id == project.pid_po
    )).first()

    if not access:
        return False

    # Check permission levels
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_ran_projects(current_user: User, db: Session) -> List[RANProjectOUT]:
    """
    Get all RAN projects that the current user has access to.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        List[RANProject]: List of accessible RAN projects
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return db.query(RanProject).all()

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.Ranproject_id for access in user_accesses]

    # Return projects that match those IDs
    return db.query(RanProject).filter(RanProject.pid_po.in_(accessible_project_ids)).all()


@RANProjectRoute.post("", response_model=CreateRANProject)
def add_ran_project(
        project_data: CreateRANProject,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new RAN project. Only senior_admin can create projects.
    """
    # Only senior_admin can create projects
    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action. Contact the Senior Admin."
        )

    pid_po = project_data.pid + project_data.po
    existing_project = db.query(RanProject).filter(RanProject.pid_po == pid_po).first()
    if existing_project:
        raise HTTPException(status_code=400, detail="RAN Project already exists")

    try:
        new_project_db = RanProject(
            pid_po=pid_po,
            project_name=project_data.project_name,
            pid=project_data.pid,
            po=project_data.po
        )
        db.add(new_project_db)
        db.commit()
        db.refresh(new_project_db)
        return new_project_db
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating RAN project: {str(e)}"
        )


@RANProjectRoute.get("")
def get_ran_projects(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all RAN projects accessible to the current user.
    - senior_admin: Can see all projects
    - admin: Can see only projects they have access to
    - user: Can see only projects they have access to
    """
    try:
        accessible_projects = get_user_accessible_ran_projects(current_user, db)
        return accessible_projects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving RAN projects: {str(e)}"
        )


@RANProjectRoute.get("/{pid_po}")
def get_ran_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific RAN project by pid_po.
    Users can only access projects they have permission for.
    """
    project = db.query(RanProject).filter(RanProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="RAN Project not found")

    # Check if user has access to this project
    if not check_ran_project_access(current_user, project, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this RAN project. Contact the Senior Admin."
        )

    return project


@RANProjectRoute.put("/{pid_po}")
def update_ran_project(
        pid_po: str,
        update_data: UpdateRANProject,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update a RAN project.
    - senior_admin: Can update any project
    - Users with "edit" or "all" permission: Can update projects they have access to
    """
    project = db.query(RanProject).filter(RanProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="RAN Project not found")

    # Check if user has edit permission
    if not check_ran_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this RAN project. Contact the Senior Admin."
        )

    # Update the project
    try:
        if update_data.project_name:
            project.project_name = update_data.project_name

        db.commit()
        db.refresh(project)
        return project
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating RAN project: {str(e)}"
        )


@RANProjectRoute.delete("/{pid_po}")
def delete_ran_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a RAN project.
    - senior_admin: Can delete any project
    - Users with "all" permission: Can delete projects they have full access to
    """
    project = db.query(RanProject).filter(RanProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="RAN Project not found")

    # Check if user has "all" permission (required for deletion)
    if not check_ran_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this RAN project. Contact the Senior Admin."
        )

    # Delete the project
    try:
        db.delete(project)
        db.commit()
        return {"message": f"RAN Project '{pid_po}' deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting RAN project: {str(e)}"
        )


@RANProjectRoute.get("/check-permission/{pid_po}")
def check_user_ran_project_permission(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Check what permissions the current user has for a specific RAN project.
    Returns the permission level and available actions.
    """
    project = db.query(RanProject).filter(RanProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="RAN Project not found")

    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return {
            "project_id": pid_po,
            "permission_level": "all",
            "can_view": True,
            "can_edit": True,
            "can_delete": True,
            "role": "senior_admin"
        }

    # Check access for other users
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ranproject_id == project.pid_po
    ).first()

    if not access:
        return {
            "project_id": pid_po,
            "permission_level": "none",
            "can_view": False,
            "can_edit": False,
            "can_delete": False,
            "role": current_user.role.name
        }

    # Determine capabilities based on permission level and role
    can_edit = (current_user.role.name == "admin" and
                access.permission_level in ["edit", "all"])
    can_delete = (current_user.role.name == "admin" and
                  access.permission_level == "all")

    return {
        "project_id": pid_po,
        "permission_level": access.permission_level,
        "can_view": True,
        "can_edit": can_edit,
        "can_delete": can_delete,
        "role": current_user.role.name
    }