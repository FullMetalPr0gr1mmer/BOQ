from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io

from APIs.Core import safe_int, get_db
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
# CRUD Methods (Refactored from ranlvl3.py)
# --------------------------------------------------------------------------------

def get_ranlvl3(db: Session, ranlvl3_id: int):
    return db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()


def get_ranlvl3_by_project_id(db: Session, project_id: str):
    return db.query(RANLvl3).filter(RANLvl3.project_id == project_id).all()


def get_all_ranlvl3(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None):
    query = db.query(RANLvl3)
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

    # Remove the code that manages child items here
    # The parent's PUT endpoint should not touch children
    # Child item updates and deletions are handled by their own endpoints

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
# New API Endpoints for Child Items
# --------------------------------------------------------------------------------

@RANLvl3Router.put("/{ranlvl3_id}/items/{item_id}", response_model=ItemsForRANLvl3InDB)
def update_ran_lvl3_item(
        ranlvl3_id: int,
        item_id: int,
        item_data: ItemsForRANLvl3Update,
        db: Session = Depends(get_db)
):
    """
    Update a specific child item for a RAN Level 3 record.
    """
    db_item = db.query(ItemsForRANLvl3).filter(
        ItemsForRANLvl3.id == item_id,
        ItemsForRANLvl3.ranlvl3_id == ranlvl3_id
    ).first()

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found for this RAN Level 3 record"
        )

    # Update fields from the payload
    update_data = item_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)

    # Recalculate parent totals after update
    parent_ranlvl3 = db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()
    if parent_ranlvl3:
        all_items = db.query(ItemsForRANLvl3).filter(ItemsForRANLvl3.ranlvl3_id == ranlvl3_id).all()
        total_quantity = sum(item.quantity for item in all_items if item.quantity is not None)
        total_price = sum(item.price for item in all_items if item.price is not None)

        parent_ranlvl3.total_quantity = total_quantity
        parent_ranlvl3.total_price = total_price
        db.commit()
        db.refresh(parent_ranlvl3)

    return db_item


@RANLvl3Router.delete("/{ranlvl3_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_lvl3_item(
        ranlvl3_id: int,
        item_id: int,
        db: Session = Depends(get_db)
):
    """
    Delete a specific child item for a RAN Level 3 record.
    """
    db_item = db.query(ItemsForRANLvl3).filter(
        ItemsForRANLvl3.id == item_id,
        ItemsForRANLvl3.ranlvl3_id == ranlvl3_id
    ).first()

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found for this RAN Level 3 record"
        )

    db.delete(db_item)
    db.commit()

    # Recalculate parent totals after deletion
    parent_ranlvl3 = db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()
    if parent_ranlvl3:
        all_items = db.query(ItemsForRANLvl3).filter(ItemsForRANLvl3.ranlvl3_id == ranlvl3_id).all()
        total_quantity = sum(item.quantity for item in all_items if item.quantity is not None)
        total_price = sum(item.price for item in all_items if item.price is not None)

        parent_ranlvl3.total_quantity = total_quantity
        parent_ranlvl3.total_price = total_price
        db.commit()
        db.refresh(parent_ranlvl3)

    return {"message": "Item deleted successfully"}


# --------------------------------------------------------------------------------
# API Endpoints (Existing)
# --------------------------------------------------------------------------------

@RANLvl3Router.post("/", response_model=RANLvl3InDB, status_code=status.HTTP_201_CREATED)
def create_ran_lvl3(
        ranlvl3_data: RANLvl3Create,
        db: Session = Depends(get_db)
):
    """
    Create a new RAN Level 3 record with its child items.
    """
    db_ranlvl3 = create_ranlvl3(db=db, ranlvl3=ranlvl3_data)
    if not db_ranlvl3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating RAN Level 3 record"
        )
    return db_ranlvl3


@RANLvl3Router.get("", response_model=PaginatedRANLvl3Response)
def get_all_ran_lvl3(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        search: Optional[str] = Query(None, min_length=1),
        db: Session = Depends(get_db)
):
    """
    Retrieve all RAN Level 3 records with pagination and optional search.
    """
    result = get_all_ranlvl3(db=db, skip=skip, limit=limit, search=search)
    return PaginatedRANLvl3Response(total=result["total"], records=result["records"])


@RANLvl3Router.get("/{ranlvl3_id}", response_model=RANLvl3InDB)
def get_ran_lvl3_by_id(
        ranlvl3_id: int,
        db: Session = Depends(get_db)
):
    """
    Retrieve a single RAN Level 3 record by its ID.
    """
    db_ranlvl3 = get_ranlvl3(db=db, ranlvl3_id=ranlvl3_id)
    if db_ranlvl3 is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Level 3 record not found")
    return db_ranlvl3


@RANLvl3Router.put("/{ranlvl3_id}", response_model=RANLvl3InDB)
def update_ran_lvl3(
        ranlvl3_id: int,
        ranlvl3_data: RANLvl3Update,
        db: Session = Depends(get_db)
):
    """
    Update an existing RAN Level 3 record and its child items.
    """
    db_ranlvl3 = update_ranlvl3(db=db, ranlvl3_id=ranlvl3_id, ranlvl3_data=ranlvl3_data)
    if db_ranlvl3 is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Level 3 record not found")
    return db_ranlvl3


@RANLvl3Router.delete("/{ranlvl3_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_lvl3(
        ranlvl3_id: int,
        db: Session = Depends(get_db)
):
    """
    Delete a RAN Level 3 record by its ID.
    """
    success = delete_ranlvl3(db=db, ranlvl3_id=ranlvl3_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Level 3 record not found")
    return {"message": "RAN Level 3 record deleted successfully"}


@RANLvl3Router.post("/{ranlvl3_id}/items/upload-csv", response_model=dict)
def upload_items_csv_to_ranlvl3(ranlvl3_id: int, file: UploadFile, db: Session = Depends(get_db)):
    """
    Uploads a CSV file to bulk-add items to a RANLvl3 record.
    """
    ranlvl3 = db.query(RANLvl3).filter(RANLvl3.id == ranlvl3_id).first()
    if not ranlvl3:
        raise HTTPException(status_code=404, detail="RANLvl3 record not found")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")

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
                category=row.get('L1 Category'),  # Hardcoded as requested
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

    # Recalculate totals after successful commit
    # all_items = db.query(ItemsForRANLvl3).filter(ItemsForRANLvl3.ranlvl3_id == ranlvl3_id).all()
    # total_quantity = sum(item.quantity for item in all_items if item.quantity is not None)
    # total_price = sum(item.price for item in all_items if item.price is not None)

    # ranlvl3.total_quantity = total_quantity
    # ranlvl3.total_price = total_price
    db.commit()
    db.refresh(ranlvl3)

    return {"message": "CSV uploaded and records created successfully", "inserted": inserted_count}