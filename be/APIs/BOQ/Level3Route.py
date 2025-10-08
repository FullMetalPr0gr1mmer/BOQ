from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from APIs.Core import get_db, get_current_user
from Models.BOQ.Levels import Lvl3, ItemsForLvl3
from Models.BOQ.Project import Project
from Models.Admin.User import User, UserProjectAccess
from Schemas.BOQ.LevelsSchema import Lvl3Create, Lvl3Out, Lvl3Update, ItemsForLvl3Create, ItemsForLvl3Out

router = APIRouter(prefix="/lvl3", tags=["Lvl3"])


def check_project_access(current_user: User, project_id: str, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project with required permission level.

    Args:
        current_user: The current user
        project_id: The project ID to check access for
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
        UserProjectAccess.project_id == project_id
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


def verify_project_exists_and_access(project_id: str, current_user: User, db: Session,
                                     required_permission: str = "view"):
    """
    Verify that project exists and user has required access.

    Args:
        project_id: Project ID to verify
        current_user: Current user
        db: Database session
        required_permission: Required permission level

    Returns:
        Project: The project object if access is granted

    Raises:
        HTTPException: If project doesn't exist or user lacks permission
    """
    project = db.query(Project).filter(Project.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_project_access(current_user, project_id, db, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not authorized to {required_permission} this project. Contact the Senior Admin."
        )

    return project


def get_user_accessible_projects(current_user: User, db: Session) -> List[str]:
    """
    Get all project IDs that the current user has access to.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        List[str]: List of accessible project IDs
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        projects = db.query(Project).all()
        return [project.pid_po for project in projects]

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    return [access.project_id for access in user_accesses]


# ---------- CREATE LVL3 ----------
@router.post("/create", response_model=Lvl3Out)
def create_lvl3(
        payload: Lvl3Create,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new Lvl3 record.
    - senior_admin: Can create Lvl3 for any project
    - Users with "edit" or "all" permission: Can create Lvl3 for projects they have access to
    """
    # Verify project exists and user has edit access
    verify_project_exists_and_access(payload.project_id, current_user, db, "edit")

    try:
        lvl3 = Lvl3(
            project_id=payload.project_id,
            project_name=payload.project_name,
            item_name=payload.item_name,
            uom=payload.uom,
            upl_line=payload.upl_line,
            total_quantity=payload.total_quantity,
            total_price=payload.total_price,
        )
        lvl3.service_type = payload.service_type or []

        db.add(lvl3)
        db.commit()
        db.refresh(lvl3)
        return lvl3
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating Lvl3 record: {str(e)}"
        )


# ---------- GET ALL ----------
@router.get("/", response_model=List[Lvl3Out])
def get_all_lvl3(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all Lvl3 records accessible to the current user.
    - senior_admin: Can see all Lvl3 records
    - admin/user: Can see only Lvl3 records for projects they have access to
    """
    try:
        accessible_project_ids = get_user_accessible_projects(current_user, db)

        if not accessible_project_ids:
            return []

        lvl3_records = db.query(Lvl3).filter(Lvl3.project_id.in_(accessible_project_ids)).all()
        return lvl3_records
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving Lvl3 records: {str(e)}"
        )


# ---------- GET BY ID ----------
@router.get("/{lvl3_id}", response_model=Lvl3Out)
def get_lvl3_by_id(
        lvl3_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific Lvl3 record by ID.
    Users can only access Lvl3 records for projects they have permission for.
    """
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has access to the project this Lvl3 belongs to
    if not check_project_access(current_user, lvl3.project_id, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this Lvl3 record. Contact the Senior Admin."
        )

    return lvl3


# ---------- UPDATE LVL3 ----------
@router.put("/{lvl3_id}", response_model=Lvl3Out)
def update_lvl3(
        lvl3_id: int,
        payload: Lvl3Update,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update a Lvl3 record.
    - senior_admin: Can update any Lvl3 record
    - Users with "edit" or "all" permission: Can update Lvl3 records for projects they have access to
    """
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has edit permission for the project this Lvl3 belongs to
    if not check_project_access(current_user, lvl3.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this Lvl3 record. Contact the Senior Admin."
        )

    try:
        for field, value in payload.dict(exclude_unset=True).items():
            if field == "service_type":
                lvl3.service_type = value or []
            else:
                setattr(lvl3, field, value)

        db.commit()
        db.refresh(lvl3)
        return lvl3
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating Lvl3 record: {str(e)}"
        )


# ---------- DELETE LVL3 ----------
@router.delete("/{lvl3_id}")
def delete_lvl3(
        lvl3_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a Lvl3 record.
    - senior_admin: Can delete any Lvl3 record
    - Users with "all" permission: Can delete Lvl3 records for projects they have full access to
    """
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has "all" permission (required for deletion)
    if not check_project_access(current_user, lvl3.project_id, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this Lvl3 record. Contact the Senior Admin."
        )

    try:
        db.delete(lvl3)
        db.commit()
        return {"detail": "Lvl3 deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting Lvl3 record: {str(e)}"
        )


# --- ITEMS ENDPOINTS WITH ADMINISTRATION ---

# ---------- ADD ITEM TO LVL3 ----------
@router.post("/{lvl3_id}/items", response_model=ItemsForLvl3Out)
def add_item_to_lvl3(
        lvl3_id: int,
        payload: ItemsForLvl3Create,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Add an item to a Lvl3 record.
    - senior_admin: Can add items to any Lvl3 record
    - Users with "edit" or "all" permission: Can add items to Lvl3 records for projects they have access to
    """
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has edit permission for the project this Lvl3 belongs to
    if not check_project_access(current_user, lvl3.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to add items to this Lvl3 record. Contact the Senior Admin."
        )

    try:
        new_item = ItemsForLvl3(
            lvl3_id=lvl3_id,
            item_name=payload.item_name,
            item_details=payload.item_details,
            vendor_part_number=payload.vendor_part_number,
            category=payload.category,
            uom=payload.uom,
            upl_line=payload.upl_line,
            quantity=payload.quantity,
            price=payload.price,
        )
        new_item.service_type = payload.service_type or []

        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding item to Lvl3 record: {str(e)}"
        )


# ---------- BULK ADD ITEMS TO LVL3 ----------
@router.post("/{lvl3_id}/items/bulk", response_model=List[ItemsForLvl3Out])
def bulk_add_items_to_lvl3(
        lvl3_id: int,
        items_payload: List[ItemsForLvl3Create],
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Bulk add items to a Lvl3 record.
    - senior_admin: Can bulk add items to any Lvl3 record
    - admin: Can bulk add items only to Lvl3 records for projects they have "edit" or "all" permission for
    - Users with "edit" or "all" permission: Can bulk add items to Lvl3 records for projects they have access to
    """
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has edit permission for the project this Lvl3 belongs to
    if not check_project_access(current_user, lvl3.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to bulk add items to this Lvl3 record. Contact the Senior Admin."
        )

    try:
        new_items = []
        for payload in items_payload:
            new_item = ItemsForLvl3(
                lvl3_id=lvl3_id,
                item_name=payload.item_name,
                item_details=payload.item_details,
                vendor_part_number=payload.vendor_part_number,
                category=payload.category,
                uom=payload.uom,
                upl_line=payload.upl_line,
                quantity=payload.quantity,
                price=payload.price,
            )
            new_item.service_type = payload.service_type or []
            new_items.append(new_item)

        db.add_all(new_items)
        db.commit()

        # After adding new items, you might want to recalculate totals
        # all_items = db.query(ItemsForLvl3).filter(ItemsForLvl3.lvl3_id == lvl3_id).all()
        # total_quantity = sum(item.quantity for item in all_items if item.quantity is not None)
        # total_price = sum(item.price for item in all_items if item.price is not None)
        # lvl3.total_quantity = total_quantity
        # lvl3.total_price = total_price

        db.commit()

        for item in new_items:
            db.refresh(item)
        db.refresh(lvl3)

        return new_items
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error bulk adding items to Lvl3 record: {str(e)}"
        )


# ---------- UPDATE ITEM FOR LVL3 ----------
@router.put("/{lvl3_id}/items/{item_id}", response_model=ItemsForLvl3Out)
def update_item_for_lvl3(
        lvl3_id: int,
        item_id: int,
        payload: ItemsForLvl3Create,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update an item for a Lvl3 record.
    - senior_admin: Can update items in any Lvl3 record
    - Users with "edit" or "all" permission: Can update items in Lvl3 records for projects they have access to
    """
    item = db.query(ItemsForLvl3).filter(ItemsForLvl3.id == item_id, ItemsForLvl3.lvl3_id == lvl3_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found for this Lvl3")

    # Get the Lvl3 record to check project access
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has edit permission for the project this Lvl3 belongs to
    if not check_project_access(current_user, lvl3.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update items in this Lvl3 record. Contact the Senior Admin."
        )

    try:
        for field, value in payload.dict(exclude_unset=True).items():
            if field == "service_type":
                item.service_type = value or []
            else:
                setattr(item, field, value)

        db.commit()
        db.refresh(item)
        return item
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating item in Lvl3 record: {str(e)}"
        )


# ---------- DELETE ITEM FOR LVL3 ----------
@router.delete("/{lvl3_id}/items/{item_id}")
def delete_item_for_lvl3(
        lvl3_id: int,
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete an item from a Lvl3 record.
    - senior_admin: Can delete items from any Lvl3 record
    - admin: Can delete items only from Lvl3 records for projects they have "all" permission for
    - Users with "all" permission: Can delete items from Lvl3 records for projects they have full access to
    """
    item = db.query(ItemsForLvl3).filter(ItemsForLvl3.id == item_id, ItemsForLvl3.lvl3_id == lvl3_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found for this Lvl3")

    # Get the Lvl3 record to check project access
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has "all" permission (required for deletion)
    if not check_project_access(current_user, lvl3.project_id, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete items from this Lvl3 record. Contact the Senior Admin."
        )

    try:
        db.delete(item)
        db.commit()
        return {"detail": "Item deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting item from Lvl3 record: {str(e)}"
        )


# ---------- SEARCH ITEMS ----------
@router.get("/search/items", response_model=List[ItemsForLvl3Out])
def search_items(
        name: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Search items across all accessible projects.
    Users can only search items from projects they have access to.
    """
    try:
        accessible_project_ids = get_user_accessible_projects(current_user, db)

        if not accessible_project_ids:
            return []

        # Get Lvl3 records from accessible projects
        accessible_lvl3_ids = db.query(Lvl3.id).filter(Lvl3.project_id.in_(accessible_project_ids)).subquery()

        # Search items only from accessible Lvl3 records
        results = db.query(ItemsForLvl3).filter(
            ItemsForLvl3.lvl3_id.in_(accessible_lvl3_ids),
            ItemsForLvl3.item_name.ilike(f"%{name}%")
        ).all()

        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching items: {str(e)}"
        )


# ---------- GET ITEMS BY LVL3 ID ----------
@router.get("/{lvl3_id}/items", response_model=List[ItemsForLvl3Out])
def get_items_for_lvl3(
        lvl3_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all items for a specific Lvl3 record.
    Users can only access items for Lvl3 records in projects they have permission for.
    """
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Check if user has access to the project this Lvl3 belongs to
    if not check_project_access(current_user, lvl3.project_id, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access items for this Lvl3 record. Contact the Senior Admin."
        )

    try:
        items = db.query(ItemsForLvl3).filter(ItemsForLvl3.lvl3_id == lvl3_id).all()
        return items
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving items for Lvl3 record: {str(e)}"
        )


# ---------- CHECK LVL3 PERMISSIONS ----------
@router.get("/check_permission/{lvl3_id}")
def check_lvl3_permission(
        lvl3_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Check what permissions the current user has for a specific Lvl3 record.
    Returns the permission level and available actions.
    """
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return {
            "lvl3_id": lvl3_id,
            "project_id": lvl3.project_id,
            "permission_level": "all",
            "can_view": True,
            "can_edit": True,
            "can_delete": True,
            "role": "senior_admin"
        }

    # Check access for other users
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == lvl3.project_id
    ).first()

    if not access:
        return {
            "lvl3_id": lvl3_id,
            "project_id": lvl3.project_id,
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
        "lvl3_id": lvl3_id,
        "project_id": lvl3.project_id,
        "permission_level": access.permission_level,
        "can_view": True,
        "can_edit": can_edit,
        "can_delete": can_delete,
        "role": current_user.role.name
    }