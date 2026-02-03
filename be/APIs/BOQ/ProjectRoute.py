# routes/projectRoute.py
from fastapi import status
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from APIs.Core import get_current_user, get_db
from Models.BOQ.Project import Project
from Models.Admin.User import User, UserProjectAccess
from Schemas.BOQ.ProjectSchema import CreateProject, UpdateProject, UpdatePOSchema, UpdatePOResponse
from Models.BOQ.Levels import Lvl3
from Models.BOQ.LLD import LLD
from Models.BOQ.BOQReference import BOQReference
from Models.BOQ.Inventory import Inventory
from Models.BOQ.Site import Site
from Models.BOQ.Dismantling import Dismantling
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
    # Senior admin has all permissions to all projects
    if current_user.role.name == "senior_admin":
        return True

    # Admin has all permissions but only to projects they have access to
    # Check UserProjectAccess for both admin and other roles
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == project.pid_po
    ).first()

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

    # Determine capabilities based on permission level (not role)
    # Users with "edit" or "all" permission can edit
    # Users with "all" permission can delete
    can_edit = access.permission_level in ["edit", "all"]
    can_delete = access.permission_level == "all"

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


@projectRoute.put("/{old_pid_po}/update-po", response_model=UpdatePOResponse)
def update_project_purchase_order(
        old_pid_po: str,
        update_data: UpdatePOSchema,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update the Purchase Order (PO) for a MW project with cascading updates.
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
    project = db.query(Project).filter(Project.pid_po == old_pid_po).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MW Project with pid_po '{old_pid_po}' not found"
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
    existing_project = db.query(Project).filter(Project.pid_po == new_pid_po).first()
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A project with pid_po '{new_pid_po}' already exists. Cannot proceed with update."
        )

    try:
        # Track affected records - count them first before any updates
        affected_tables = {}
        lvl3_count = db.query(Lvl3).filter(Lvl3.project_id == old_pid_po).count()
        lld_count = db.query(LLD).filter(LLD.pid_po == old_pid_po).count()
        boq_reference_count = db.query(BOQReference).filter(BOQReference.pid_po == old_pid_po).count()
        inventory_count = db.query(Inventory).filter(Inventory.pid_po == old_pid_po).count()
        site_count = db.query(Site).filter(Site.project_id == old_pid_po).count()
        dismantling_count = db.query(Dismantling).filter(Dismantling.pid_po == old_pid_po).count()
        user_access_count = db.query(UserProjectAccess).filter(UserProjectAccess.project_id == old_pid_po).count()

        # STEP 1: Update the project itself FIRST (create the new primary key)
        # Add a new project with the new pid_po
        new_project = Project(
            pid_po=new_pid_po,
            pid=project.pid,
            po=new_po,
            project_name=project.project_name
        )
        db.add(new_project)
        db.flush()  # Make the new project available for foreign key references

        # STEP 2: Now update all foreign key references to point to the new pid_po
        # Update Lvl3 records (uses project_id)
        db.query(Lvl3).filter(Lvl3.project_id == old_pid_po).update(
            {"project_id": new_pid_po}, synchronize_session=False
        )
        affected_tables["lvl3"] = lvl3_count

        # Update LLD records (uses pid_po)
        db.query(LLD).filter(LLD.pid_po == old_pid_po).update(
            {"pid_po": new_pid_po}, synchronize_session=False
        )
        affected_tables["lld"] = lld_count

        # Update BOQReference records (uses pid_po)
        db.query(BOQReference).filter(BOQReference.pid_po == old_pid_po).update(
            {"pid_po": new_pid_po}, synchronize_session=False
        )
        affected_tables["boq_reference"] = boq_reference_count

        # Update Inventory records (uses pid_po)
        db.query(Inventory).filter(Inventory.pid_po == old_pid_po).update(
            {"pid_po": new_pid_po}, synchronize_session=False
        )
        affected_tables["inventory"] = inventory_count

        # Update Site records (uses project_id)
        db.query(Site).filter(Site.project_id == old_pid_po).update(
            {"project_id": new_pid_po}, synchronize_session=False
        )
        affected_tables["site"] = site_count

        # Update Dismantling records (uses pid_po)
        db.query(Dismantling).filter(Dismantling.pid_po == old_pid_po).update(
            {"pid_po": new_pid_po}, synchronize_session=False
        )
        affected_tables["dismantling"] = dismantling_count

        # Update UserProjectAccess records (uses project_id)
        db.query(UserProjectAccess).filter(UserProjectAccess.project_id == old_pid_po).update(
            {"project_id": new_pid_po}, synchronize_session=False
        )
        affected_tables["user_project_access"] = user_access_count

        # STEP 3: Delete the old project record (now that all foreign keys point to new one)
        db.delete(project)

        # Commit all changes atomically
        db.commit()
        db.refresh(new_project)

        # Calculate total records updated
        total_records_updated = sum(affected_tables.values())

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