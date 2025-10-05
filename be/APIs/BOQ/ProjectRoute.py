# routes/projectRoute.py
from fastapi import status
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from APIs.Core import get_current_user, get_db
from Models.BOQ.Project import Project
from Models.Admin.User import User, UserProjectAccess
from Schemas.BOQ.ProjectSchema import CreateProject, UpdateProject
from typing import List

projectRoute = APIRouter(tags=["Projects"])


def check_project_access(current_user: User, project: Project, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project with required permission level.

    Args:
        current_user: The current user
        project: The project to check access for
        db: Database session
        required_permission: Required permission level ("view", "edit", "all")

    Returns:
        bool: True if user has access, False otherwise
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == project.pid_po  # Assuming project_id stores pid_po
    ).first()

    if not access:
        return False

    # Check permission levels
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


@projectRoute.post("/create_project", response_model=CreateProject)
def add_project(
        project_data: CreateProject,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new project. Only senior_admin can create projects.
    """
    # Only senior_admin can create projects
    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action. Contact the Senior Admin."
        )

    pid_po = project_data.pid + project_data.po
    existing_project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if existing_project:
        raise HTTPException(status_code=400, detail="Project already exists")

    new_project_db = Project(
        pid_po=pid_po,
        project_name=project_data.project_name,
        pid=project_data.pid,
        po=project_data.po
    )
    db.add(new_project_db)
    db.commit()
    db.refresh(new_project_db)
    return new_project_db


@projectRoute.get("/get_project")
def get_projects(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all projects accessible to the current user.
    - senior_admin: Can see all projects
    - admin: Can see only projects they have access to
    - user: Can see only projects they have access to
    """
    try:
        accessible_projects = get_user_accessible_projects(current_user, db)
        return accessible_projects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving projects: {str(e)}"
        )


@projectRoute.get("/get_project/{pid_po}")
def get_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific project by pid_po.
    Users can only access projects they have permission for.
    """
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user has access to this project
    if not check_project_access(current_user, project, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this project. Contact the Senior Admin."
        )

    return project


@projectRoute.put("/update_project/{pid_po}")
def update_project(
        pid_po: str,
        update_data: UpdateProject,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update a project.
    - senior_admin: Can update any project
    - Users with "edit" or "all" permission: Can update projects they have access to
    """
    print('///////////////////////////////////////////////////')
    print(update_data)

    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user has edit permission
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this project. Contact the Senior Admin."
        )

    # Update the project
    try:
        if update_data.project_name:
            project.project_name = update_data.project_name


            # Update pid_po if pid or po changed


        db.commit()
        db.refresh(project)
        return project
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating project: {str(e)}"
        )


@projectRoute.delete("/delete_project/{pid_po}")
def delete_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a project.
    - senior_admin: Can delete any project
    - Users with "all" permission: Can delete projects they have full access to
    """
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user has "all" permission (required for deletion)
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this project. Contact the Senior Admin."
        )

    # Delete the project
    try:
        db.delete(project)
        db.commit()
        return {"message": f"Project '{pid_po}' deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )


# Additional endpoint to check user's permission for a specific project
@projectRoute.get("/check_project_permission/{pid_po}")
def check_user_project_permission(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Check what permissions the current user has for a specific project.
    Returns the permission level and available actions.
    """
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
        UserProjectAccess.project_id == project.pid_po
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


def get_project_for_boq(
        pid_po: str,
        db: Session = Depends(get_db)
):
    """
    Get a specific project by pid_po.
    Users can only access projects they have permission for.
    """
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    return project