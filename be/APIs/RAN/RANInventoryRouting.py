from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io

from APIs.Core import safe_int, get_db
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
# CRUD Methods
# --------------------------------------------------------------------------------

def get_raninventory(db: Session, raninventory_id: int):
    return db.query(RANInventory).filter(RANInventory.id == raninventory_id).first()


def get_all_raninventory(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None):
    query = db.query(RANInventory)
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
        db: Session = Depends(get_db)
):
    """
    Create a new RAN Inventory record.
    """
    db_raninventory = create_raninventory(db=db, raninventory=raninventory_data)
    if not db_raninventory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating RAN Inventory record"
        )
    return db_raninventory


@RANInventoryRouter.get("", response_model=PaginatedRANInventoryResponse)
def get_all_ran_inventory_records(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        search: Optional[str] = Query(None, min_length=1),
        db: Session = Depends(get_db)
):
    """
    Retrieve all RAN Inventory records with pagination and optional search.
    """
    result = get_all_raninventory(db=db, skip=skip, limit=limit, search=search)
    return PaginatedRANInventoryResponse(total=result["total"], records=result["records"])


@RANInventoryRouter.get("/{raninventory_id}", response_model=RANInventoryInDB)
def get_ran_inventory_by_id(
        raninventory_id: int,
        db: Session = Depends(get_db)
):
    """
    Retrieve a single RAN Inventory record by its ID.
    """
    db_raninventory = get_raninventory(db=db, raninventory_id=raninventory_id)
    if db_raninventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")
    return db_raninventory


@RANInventoryRouter.put("/{raninventory_id}", response_model=RANInventoryInDB)
def update_ran_inventory_record(
        raninventory_id: int,
        raninventory_data: RANInventoryUpdate,
        db: Session = Depends(get_db)
):
    """
    Update an existing RAN Inventory record.
    """
    db_raninventory = update_raninventory(db=db, raninventory_id=raninventory_id, raninventory_data=raninventory_data)
    if db_raninventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")
    return db_raninventory


@RANInventoryRouter.delete("/{raninventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_inventory_record(
        raninventory_id: int,
        db: Session = Depends(get_db)
):
    """
    Delete a RAN Inventory record by its ID.
    """
    success = delete_raninventory(db=db, raninventory_id=raninventory_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")
    return {"message": "RAN Inventory record deleted successfully"}


@RANInventoryRouter.post("/upload-csv", response_model=dict)
def upload_ran_inventory_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads a CSV file to bulk-add RAN Inventory records.
    The CSV must have headers matching the RANInventory schema fields.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")

    try:
        contents = file.file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(contents))

        new_records = []
        for row in csv_reader:
            new_record = RANInventory(
                mrbts=row.get('MRBTS'),
                site_id=row.get('Site ID'),
                identification_code=row.get('identificationCode'),
                user_label=row.get('userLabel'),
                serial_number=row.get('serialNumber'),
                duplicate=True if row.get('Duplicate') else False,
                duplicate_remarks=row.get('Duplicate remarks'),
            )
            new_records.append(new_record)

        db.add_all(new_records)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error processing CSV file: {e}")

    return {"message": f"Successfully added {len(new_records)} records from CSV."}
