from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io

from APIs.Core import safe_int, get_db, get_current_user
from Models.Admin.User import UserProjectAccess, User
from Schemas.RAN.RANLvl3Schema import (
    RANLvl3Create,
    RANLvl3InDB,
    RANLvl3Update,
    PaginatedRANLvl3Response,
    ItemsForRANLvl3Update,
    ItemsForRANLvl3InDB,
)
from Models.RAN.RANLvl3 import RANLvl3, ItemsForRANLvl3

RANLvl3Router = APIRouter(
    prefix="/ranlvl3",
    tags=["RANLvl3"]
)


# --------------------------------------------------------------------------------
# Access Control Helper Functions
# --------------------------------------------------------------------------------

def check_ranlvl3_project_access(current_user: User, project_id: str, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project for RANLvl3 operations.
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ranproject_id == project_id
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


def get_accessible_projects_for_user(current_user: User, db: Session):
    """
    Get all project IDs that the current user has access to.
    """
    if current_user.role.name == "senior_admin":
        return None  # Senior admin can access all projects

    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    return [access.Ranproject_id for access in user_accesses]


# --------------------------------------------------------------------------------
# CRUD Methods (Refactored from ranlvl3.py)
# --------------------------------------------------------------------------------

def get_ranlvl3(db: Session, ranlvl3_id: int):
    return db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()


def get_ranlvl3_by_project_id(db: Session, project_id: str):
    return db.query(RANLvl3).filter(RANLvl3.project_id == project_id).all()


def get_all_ranlvl3(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None,
                    accessible_projects: List[str] = None):
    query = db.query(RANLvl3)

    # Filter by accessible projects if not senior admin
    if accessible_projects is not None:
        if not accessible_projects:  # Empty list means no access
            return {"total": 0, "records": []}
        query = query.filter(RANLvl3.project_id.in_(accessible_projects))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            RANLvl3.item_name.ilike(search_pattern)
        )

    total = query.count()
    records = query.order_by(RANLvl3.id).offset(skip).limit(limit).all()
    return {"total": total, "records": records}


def create_ranlvl3(db: Session, ranlvl3: RANLvl3Create):
    db_ranlvl3 = RANLvl3(
        project_id=ranlvl3.project_id,
        item_name=ranlvl3.item_name,
        key=ranlvl3.key,
        uom=ranlvl3.uom,
        total_quantity=ranlvl3.total_quantity,
        total_price=ranlvl3.total_price,
        category=ranlvl3.category,
        po_line=ranlvl3.po_line,
        upl_line=ranlvl3.upl_line
    )
    db_ranlvl3.service_type = ranlvl3.service_type

    for item in ranlvl3.items:
        db_item = ItemsForRANLvl3(
            item_name=item.item_name,
            item_details=item.item_details,
            vendor_part_number=item.vendor_part_number,
            category=item.category,
            uom=item.uom,
            quantity=item.quantity,
            price=item.price,
            upl_line=item.upl_line
        )
        db_item.service_type = item.service_type
        db_ranlvl3.items.append(db_item)

    db.add(db_ranlvl3)
    db.commit()
    db.refresh(db_ranlvl3)
    return db_ranlvl3


def update_ranlvl3(db: Session, ranlvl3_id: int, ranlvl3_data: RANLvl3Update):
    db_ranlvl3 = get_ranlvl3(db, ranlvl3_id)
    if not db_ranlvl3:
        return None

    # Only update the parent's attributes
    db_ranlvl3.project_id = ranlvl3_data.project_id
    db_ranlvl3.item_name = ranlvl3_data.item_name
    db_ranlvl3.key = ranlvl3_data.key
    db_ranlvl3.uom = ranlvl3_data.uom
    db_ranlvl3.total_quantity = ranlvl3_data.total_quantity
    db_ranlvl3.total_price = ranlvl3_data.total_price
    db_ranlvl3.service_type = ranlvl3_data.service_type
    db_ranlvl3.category = ranlvl3_data.category
    db_ranlvl3.po_line = ranlvl3_data.po_line,
    db_ranlvl3.upl_line=ranlvl3_data.upl_line

    db.commit()
    db.refresh(db_ranlvl3)
    return db_ranlvl3


def delete_ranlvl3(db: Session, ranlvl3_id: int):
    db_ranlvl3 = db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()
    if not db_ranlvl3:
        return False
    db.delete(db_ranlvl3)
    db.commit()
    return True


# --------------------------------------------------------------------------------
# API Endpoints for Child Items
# --------------------------------------------------------------------------------

@RANLvl3Router.put("/{ranlvl3_id}/items/{item_id}", response_model=ItemsForRANLvl3InDB)
def update_ran_lvl3_item(
        ranlvl3_id: int,
        item_id: int,
        item_data: ItemsForRANLvl3Update,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update a specific child item for a RAN Level 3 record.
    """
    # First, get the parent record to check project access
    parent_record = db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()
    if not parent_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RAN Level 3 record not found"
        )

    # Check if user has edit permission for the project
    if not check_ranlvl3_project_access(current_user, parent_record.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to edit items in this project. Contact the Senior Admin."
        )

    # Users cannot edit items
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to update RAN Level 3 items. Contact the Senior Admin."
        )

    db_item = db.query(ItemsForRANLvl3).filter(
        ItemsForRANLvl3.id == item_id,
        ItemsForRANLvl3.ranlvl3_id == ranlvl3_id
    ).first()

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found for this RAN Level 3 record"
        )

    try:
        # Update fields from the payload
        update_data = item_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)

        db.commit()
        db.refresh(db_item)

        # Recalculate parent totals after update
        # all_items = db.query(ItemsForRANLvl3).filter(ItemsForRANLvl3.ranlvl3_id == ranlvl3_id).all()
        # total_quantity = sum(item.quantity for item in all_items if item.quantity is not None)
        # total_price = sum(item.price for item in all_items if item.price is not None)

        # parent_record.total_quantity = total_quantity
        # parent_record.total_price = total_price
        # db.commit()
        # db.refresh(parent_record)

        return db_item
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating RAN Level 3 item: {str(e)}"
        )


@RANLvl3Router.delete("/{ranlvl3_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_lvl3_item(
        ranlvl3_id: int,
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a specific child item for a RAN Level 3 record.
    """
    # First, get the parent record to check project access
    parent_record = db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()
    if not parent_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RAN Level 3 record not found"
        )

    # Check if user has all permission for the project (required for deletion)
    if not check_ranlvl3_project_access(current_user, parent_record.project_id, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete items in this project. Contact the Senior Admin."
        )

    # Users cannot delete items
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to delete RAN Level 3 items. Contact the Senior Admin."
        )

    db_item = db.query(ItemsForRANLvl3).filter(
        ItemsForRANLvl3.id == item_id,
        ItemsForRANLvl3.ranlvl3_id == ranlvl3_id
    ).first()

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found for this RAN Level 3 record"
        )

    try:
        db.delete(db_item)
        db.commit()

        # Recalculate parent totals after deletion
        # all_items = db.query(ItemsForRANLvl3).filter(ItemsForRANLvl3.ranlvl3_id == ranlvl3_id).all()
        # total_quantity = sum(item.quantity for item in all_items if item.quantity is not None)
        # total_price = sum(item.price for item in all_items if item.price is not None)

        # # parent_record.total_quantity = total_quantity
        # # parent_record.total_price = total_price
        # db.commit()
        # db.refresh(parent_record)

        return {"message": "Item deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting RAN Level 3 item: {str(e)}"
        )


# --------------------------------------------------------------------------------
# API Endpoints (Main CRUD)
# --------------------------------------------------------------------------------

@RANLvl3Router.post("/", response_model=RANLvl3InDB, status_code=status.HTTP_201_CREATED)
def create_ran_lvl3(
        ranlvl3_data: RANLvl3Create,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new RAN Level 3 record with its child items.
    """
    # Check if user has edit permission for the project
    if not check_ranlvl3_project_access(current_user, ranlvl3_data.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create RAN Level 3 records in this project. Contact the Senior Admin."
        )

    # Users cannot create records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to create RAN Level 3 records. Contact the Senior Admin."
        )

    try:
        db_ranlvl3 = create_ranlvl3(db=db, ranlvl3=ranlvl3_data)
        if not db_ranlvl3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating RAN Level 3 record"
            )
        return db_ranlvl3
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating RAN Level 3 record: {str(e)}"
        )


@RANLvl3Router.get("", response_model=PaginatedRANLvl3Response)
def get_all_ran_lvl3(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        search: Optional[str] = Query(None, min_length=1),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve all RAN Level 3 records with pagination and optional search.
    Users can only see records from projects they have access to.
    """
    try:
        accessible_projects = get_accessible_projects_for_user(current_user, db)
        result = get_all_ranlvl3(db=db, skip=skip, limit=limit, search=search, accessible_projects=accessible_projects)
        return PaginatedRANLvl3Response(total=result["total"], records=result["records"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving RAN Level 3 records: {str(e)}"
        )


@RANLvl3Router.get("/{ranlvl3_id}", response_model=RANLvl3InDB)
def get_ran_lvl3_by_id(
        ranlvl3_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve a single RAN Level 3 record by its ID.
    """
    db_ranlvl3 = get_ranlvl3(db=db, ranlvl3_id=ranlvl3_id)
    if db_ranlvl3 is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Level 3 record not found")

    # Check if user has view permission for the project
    if not check_ranlvl3_project_access(current_user, db_ranlvl3.project_id, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this RAN Level 3 record. Contact the Senior Admin."
        )

    return db_ranlvl3


@RANLvl3Router.put("/{ranlvl3_id}", response_model=RANLvl3InDB)
def update_ran_lvl3(
        ranlvl3_id: int,
        ranlvl3_data: RANLvl3Update,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update an existing RAN Level 3 record.
    """
    # First check if record exists
    existing_record = get_ranlvl3(db, ranlvl3_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Level 3 record not found")

    # Check if user has edit permission for the project
    if not check_ranlvl3_project_access(current_user, existing_record.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this RAN Level 3 record. Contact the Senior Admin."
        )

    # Users cannot update records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to update RAN Level 3 records. Contact the Senior Admin."
        )

    try:
        db_ranlvl3 = update_ranlvl3(db=db, ranlvl3_id=ranlvl3_id, ranlvl3_data=ranlvl3_data)
        return db_ranlvl3
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating RAN Level 3 record: {str(e)}"
        )


@RANLvl3Router.delete("/{ranlvl3_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_lvl3(
        ranlvl3_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a RAN Level 3 record by its ID.
    """
    # First check if record exists
    existing_record = get_ranlvl3(db, ranlvl3_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Level 3 record not found")

    # Check if user has all permission for the project (required for deletion)
    if not check_ranlvl3_project_access(current_user, existing_record.project_id, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this RAN Level 3 record. Contact the Senior Admin."
        )

    # Users cannot delete records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to delete RAN Level 3 records. Contact the Senior Admin."
        )

    try:
        success = delete_ranlvl3(db=db, ranlvl3_id=ranlvl3_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Level 3 record not found")
        return {"message": "RAN Level 3 record deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting RAN Level 3 record: {str(e)}"
        )


@RANLvl3Router.post("/{ranlvl3_id}/items/upload-csv", response_model=dict)
def upload_items_csv_to_ranlvl3(
        ranlvl3_id: int,
        file: UploadFile,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Uploads a CSV file to bulk-add items to a RANLvl3 record.
    """
    # First check if record exists and get project access
    ranlvl3 = db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()
    if not ranlvl3:
        raise HTTPException(status_code=404, detail="RANLvl3 record not found")

    # Check if user has edit permission for the project
    if not check_ranlvl3_project_access(current_user, ranlvl3.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload CSV files for this project. Contact the Senior Admin."
        )

    # Users cannot upload CSV files
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to upload CSV files. Contact the Senior Admin."
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")

    try:
        contents = file.file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(contents))

        inserted_count = 0

        for row in csv_reader:
            try:
                new_item = ItemsForRANLvl3(
                    ranlvl3_id=ranlvl3_id,
                    item_name=ranlvl3.item_name,  # Use parent's item_name
                    item_details=row.get('Item Description'),
                    vendor_part_number=row.get('Vendor Part Number'),
                    service_type=['2'],  # Hardcoded as requested
                    upl_line=row.get('UPL Line'),
                    category=row.get('L1 Category'),
                    uom=safe_int(row.get('UOM')),
                    quantity=1,
                    price=float(row.get('price')) if row.get('price') else None,
                )
                db.add(new_item)
                inserted_count += 1
            except (ValueError, KeyError) as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=f"Invalid data in CSV: {e}. Please check your CSV format.")

        db.commit()
        db.refresh(ranlvl3)

        return {"message": "CSV uploaded and records created successfully", "inserted": inserted_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading CSV: {str(e)}"
        )