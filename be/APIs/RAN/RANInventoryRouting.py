from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io

from APIs.Core import safe_int, get_db, get_current_user
from Models.Admin.User import UserProjectAccess, User
from Schemas.RAN.RANInventorySchema import (
    RANInventoryCreate,
    RANInventoryInDB,
    RANInventoryUpdate,
    PaginatedRANInventoryResponse
)
from Models.RAN.RANInventory import RANInventory

RANInventoryRouter = APIRouter(
    prefix="/raninventory",
    tags=["RANInventory"]
)


# --------------------------------------------------------------------------------
# Access Control Helper Functions
# --------------------------------------------------------------------------------

def check_raninventory_project_access(current_user: User, pid_po: str, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project for RANInventory operations.
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ranproject_id == pid_po
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


def get_accessible_projects_for_inventory(current_user: User, db: Session):
    """
    Get all project IDs that the current user has access to for inventory operations.
    """
    if current_user.role.name == "senior_admin":
        return None  # Senior admin can access all projects

    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    return [access.Ranproject_id for access in user_accesses]


# --------------------------------------------------------------------------------
# CRUD Methods
# --------------------------------------------------------------------------------

def get_raninventory(db: Session, raninventory_id: int):
    return db.query(RANInventory).filter(RANInventory.id == raninventory_id).first()


def get_all_raninventory(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None,
                         accessible_projects: List[str] = None):
    query = db.query(RANInventory)

    # Filter by accessible projects if not senior admin
    if accessible_projects is not None:
        if not accessible_projects:  # Empty list means no access
            return {"total": 0, "records": []}
        query = query.filter(RANInventory.pid_po.in_(accessible_projects))

    if search:
        search_pattern = f"%{search}%"
        # Search across multiple fields
        query = query.filter(
            RANInventory.mrbts.ilike(search_pattern) |
            RANInventory.site_id.ilike(search_pattern) |
            RANInventory.identification_code.ilike(search_pattern) |
            RANInventory.user_label.ilike(search_pattern) |
            RANInventory.serial_number.ilike(search_pattern)
        )

    total = query.count()
    records = query.order_by(RANInventory.id).offset(skip).limit(limit).all()
    return {"total": total, "records": records}


def create_raninventory(db: Session, raninventory: RANInventoryCreate):
    db_raninventory = RANInventory(**raninventory.model_dump())
    db.add(db_raninventory)
    db.commit()
    db.refresh(db_raninventory)
    return db_raninventory


def update_raninventory(db: Session, raninventory_id: int, raninventory_data: RANInventoryUpdate):
    db_raninventory = get_raninventory(db, raninventory_id)
    if not db_raninventory:
        return None

    update_data = raninventory_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_raninventory, key, value)

    db.commit()
    db.refresh(db_raninventory)
    return db_raninventory


def delete_raninventory(db: Session, raninventory_id: int):
    db_raninventory = db.query(RANInventory).filter(RANInventory.id == raninventory_id).first()
    if not db_raninventory:
        return False
    db.delete(db_raninventory)
    db.commit()
    return True


# --------------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------------

@RANInventoryRouter.post("/", response_model=RANInventoryInDB, status_code=status.HTTP_201_CREATED)
def create_ran_inventory(
        raninventory_data: RANInventoryCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new RAN Inventory record.
    """
    # Check if user has edit permission for the project (if pid_po is provided)
    if raninventory_data.pid_po:
        if not check_raninventory_project_access(current_user, raninventory_data.pid_po, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create RAN Inventory records for this project. Contact the Senior Admin."
            )

    # Users cannot create records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to create RAN Inventory records. Contact the Senior Admin."
        )

    try:
        db_raninventory = create_raninventory(db=db, raninventory=raninventory_data)
        if not db_raninventory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating RAN Inventory record"
            )
        return db_raninventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating RAN Inventory record: {str(e)}"
        )


@RANInventoryRouter.get("", response_model=PaginatedRANInventoryResponse)
def get_all_ran_inventory_records(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        search: Optional[str] = Query(None, min_length=1),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve all RAN Inventory records with pagination and optional search.
    Users can only see records from projects they have access to.
    """
    try:
        accessible_projects = get_accessible_projects_for_inventory(current_user, db)
        result = get_all_raninventory(db=db, skip=skip, limit=limit, search=search,
                                      accessible_projects=accessible_projects)
        return PaginatedRANInventoryResponse(total=result["total"], records=result["records"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving RAN Inventory records: {str(e)}"
        )


@RANInventoryRouter.get("/{raninventory_id}", response_model=RANInventoryInDB)
def get_ran_inventory_by_id(
        raninventory_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve a single RAN Inventory record by its ID.
    """
    db_raninventory = get_raninventory(db=db, raninventory_id=raninventory_id)
    if db_raninventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")

    # Check if user has view permission for the project (if pid_po exists)
    if db_raninventory.pid_po:
        if not check_raninventory_project_access(current_user, db_raninventory.pid_po, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this RAN Inventory record. Contact the Senior Admin."
            )

    return db_raninventory


@RANInventoryRouter.put("/{raninventory_id}", response_model=RANInventoryInDB)
def update_ran_inventory_record(
        raninventory_id: int,
        raninventory_data: RANInventoryUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update an existing RAN Inventory record.
    """
    # First check if record exists
    existing_record = get_raninventory(db, raninventory_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")

    # Check if user has edit permission for the project (if pid_po exists)
    if existing_record.pid_po:
        if not check_raninventory_project_access(current_user, existing_record.pid_po, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this RAN Inventory record. Contact the Senior Admin."
            )

    # Users cannot update records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to update RAN Inventory records. Contact the Senior Admin."
        )

    try:
        db_raninventory = update_raninventory(db=db, raninventory_id=raninventory_id,
                                              raninventory_data=raninventory_data)
        return db_raninventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating RAN Inventory record: {str(e)}"
        )


@RANInventoryRouter.delete("/{raninventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_inventory_record(
        raninventory_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a RAN Inventory record by its ID.
    """
    # First check if record exists
    existing_record = get_raninventory(db, raninventory_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")

    # Check if user has all permission for the project (required for deletion)
    if existing_record.pid_po:
        if not check_raninventory_project_access(current_user, existing_record.pid_po, db, "all"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this RAN Inventory record. Contact the Senior Admin."
            )

    # Users cannot delete records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to delete RAN Inventory records. Contact the Senior Admin."
        )

    try:
        success = delete_raninventory(db=db, raninventory_id=raninventory_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")
        return {"message": "RAN Inventory record deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting RAN Inventory record: {str(e)}"
        )


@RANInventoryRouter.post("/upload-csv", response_model=dict)
def upload_ran_inventory_csv(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Uploads a CSV file to bulk-add RAN Inventory records.
    The CSV must have headers matching the RANInventory schema fields.
    """
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

        new_records = []
        for row in csv_reader:
            pid_po = row.get('pid_po')

            # Check access for each record's project if pid_po is provided
            if pid_po and not check_raninventory_project_access(current_user, pid_po, db, "edit"):
                continue  # Skip records for projects the user doesn't have access to

            new_record = RANInventory(
                mrbts=row.get('MRBTS'),
                site_id=row.get('Site ID'),
                identification_code=row.get('identificationCode'),
                user_label=row.get('userLabel'),
                serial_number=row.get('serialNumber'),
                duplicate=True if row.get('Duplicate') else False,
                duplicate_remarks=row.get('Duplicate remarks'),
                pid_po=pid_po,
            )
            new_records.append(new_record)

        if new_records:
            db.add_all(new_records)
            db.commit()

        return {"message": f"Successfully added {len(new_records)} records from CSV."}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV file: {str(e)}"
        )