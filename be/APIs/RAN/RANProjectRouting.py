from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from APIs.Core import get_db, get_current_user
from Models.Admin.User import UserProjectAccess, User
from Models.RAN import RANProject
from Models.RAN.RANProject import RanProject
from Schemas.RAN.RANProjectSchema import CreateRANProject, UpdateRANProject, RANProjectOUT, UpdatePOSchema, UpdatePOResponse
from Models.RAN.RANInventory import RANInventory
from Models.RAN.RANAntennaSerials import RANAntennaSerials
from Models.RAN.RANLvl3 import RANLvl3
from Models.RAN.RAN_LLD import RAN_LLD

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


@RANProjectRoute.put("/{old_pid_po}/update-po", response_model=UpdatePOResponse)
def update_project_purchase_order(
        old_pid_po: str,
        update_data: UpdatePOSchema,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update the Purchase Order (PO) for a RAN project with cascading updates.
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
    project = db.query(RanProject).filter(RanProject.pid_po == old_pid_po).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAN Project with pid_po '{old_pid_po}' not found"
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
    existing_project = db.query(RanProject).filter(RanProject.pid_po == new_pid_po).first()
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A project with pid_po '{new_pid_po}' already exists. Cannot proceed with update."
        )

    try:
        # Track affected records - count them first before any updates
        affected_tables = {}
        inventory_count = db.query(RANInventory).filter(RANInventory.pid_po == old_pid_po).count()
        antenna_serials_count = db.query(RANAntennaSerials).filter(RANAntennaSerials.project_id == old_pid_po).count()
        lvl3_count = db.query(RANLvl3).filter(RANLvl3.project_id == old_pid_po).count()
        lld_count = db.query(RAN_LLD).filter(RAN_LLD.pid_po == old_pid_po).count()
        user_access_count = db.query(UserProjectAccess).filter(UserProjectAccess.Ranproject_id == old_pid_po).count()

        # STEP 1: Update the project itself FIRST (create the new primary key)
        # Add a new project with the new pid_po
        new_project = RanProject(
            pid_po=new_pid_po,
            pid=project.pid,
            po=new_po,
            project_name=project.project_name
        )
        db.add(new_project)
        db.flush()  # Make the new project available for foreign key references

        # STEP 2: Now update all foreign key references to point to the new pid_po
        # Update RANInventory records
        db.query(RANInventory).filter(RANInventory.pid_po == old_pid_po).update(
            {"pid_po": new_pid_po}, synchronize_session=False
        )
        affected_tables["ran_inventory"] = inventory_count

        # Update RANAntennaSerials records
        db.query(RANAntennaSerials).filter(RANAntennaSerials.project_id == old_pid_po).update(
            {"project_id": new_pid_po}, synchronize_session=False
        )
        affected_tables["ran_antenna_serials"] = antenna_serials_count

        # Update RANLvl3 records
        db.query(RANLvl3).filter(RANLvl3.project_id == old_pid_po).update(
            {"project_id": new_pid_po}, synchronize_session=False
        )
        affected_tables["ran_lvl3"] = lvl3_count

        # Update RAN_LLD records
        db.query(RAN_LLD).filter(RAN_LLD.pid_po == old_pid_po).update(
            {"pid_po": new_pid_po}, synchronize_session=False
        )
        affected_tables["ran_lld"] = lld_count

        # Update UserProjectAccess records
        db.query(UserProjectAccess).filter(UserProjectAccess.Ranproject_id == old_pid_po).update(
            {"Ranproject_id": new_pid_po}, synchronize_session=False
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