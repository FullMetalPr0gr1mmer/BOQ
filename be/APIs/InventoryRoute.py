from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import csv
from io import StringIO
import re

from APIs.Core import get_db
from Models.Site import Site
from Models.Inventory import Inventory
from Schemas.InventoySchema import AddSite, CreateInventory, InventoryOut, InventoryPagination
from pydantic import BaseModel
inventoryRoute = APIRouter(tags=["Inventory/Sites"])

# ----------------------------
# SITE CRUD
# ----------------------------

@inventoryRoute.post("/add-site")
def add_site(site_data: AddSite, db: Session = Depends(get_db)):
    existing_site = db.query(Site).filter(Site.site_id == site_data.site_id).first()
    if existing_site:
        raise HTTPException(status_code=400, detail="Site already exists")

    new_site = Site(
        site_id=site_data.site_id,
        site_name=site_data.site_name,
        project_id=site_data.pid_po
    )
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    return new_site


@inventoryRoute.get("/get-site")
def get_sites(db: Session = Depends(get_db)):
    return db.query(Site).all()


@inventoryRoute.put("/update-site/{site_id}")
def update_site(site_id: str, site_data: AddSite, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.site_id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Allow updating only site_name and project_id (not site_id)
    site.site_name = site_data.site_name
    site.project_id = site_data.pid_po
    db.commit()
    db.refresh(site)
    return site


@inventoryRoute.delete("/delete-site/{site_id}")
def delete_site(site_id: str, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.site_id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Delete all related inventory first
    db.query(Inventory).filter(Inventory.site_id == site_id).delete()
    db.delete(site)
    db.commit()
    return {"message": "Site and related inventory deleted successfully"}


# ----------------------------
# INVENTORY CRUD
# ----------------------------

# ----------------------------
# INVENTORY CRUD - REFACTORED
# ----------------------------

@inventoryRoute.post("/create-inventory", response_model=InventoryOut)
def create_inventory(inventory_data: CreateInventory, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.site_id == inventory_data.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found. Please add the site first.")

    new_inventory = Inventory(**inventory_data.dict())
    db.add(new_inventory)
    db.commit()
    db.refresh(new_inventory)
    return new_inventory


@inventoryRoute.get("/inventory", response_model=InventoryPagination)
def get_inventory(
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
):
    query = db.query(Inventory)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Inventory.site_id.like(search_pattern),
                Inventory.site_name.like(search_pattern)
            )
        )
    total_count = query.count()
    records = query.order_by(Inventory.id).offset(skip).limit(limit).all()
    return {"records": records, "total": total_count}


@inventoryRoute.put("/update-inventory/{inventory_id}", response_model=InventoryOut)
def update_inventory(inventory_id: int, inventory_data: CreateInventory, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    for field, value in inventory_data.dict().items():
        setattr(inventory, field, value)
    db.commit()
    db.refresh(inventory)
    return inventory


@inventoryRoute.delete("/delete-inventory/{inventory_id}")
def delete_inventory(inventory_id: int, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    db.delete(inventory)
    db.commit()
    return {"message": "Inventory deleted successfully"}


# ----------------------------
# CSV UPLOAD
# ----------------------------

@inventoryRoute.post("/upload-inventory-csv")
async def upload_inventory_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    content = await file.read()
    csv_reader = csv.DictReader(StringIO(content.decode("utf-8")))

    # Define a consistent mapping for CSV headers to model fields
    header_mapping = {
        'Site Id': 'site_id',
        'Site Name': 'site_name',
        'Slot Id': 'slot_id',
        'Port Id': 'port_id',
        'Status': 'status',
        'Company ID': 'company_id',
        'Mnemonic': 'mnemonic',
        'CLEI Code': 'clei_code',
        'Part No': 'part_no',
        'Software Part No': 'software_no',
        'Factory ID': 'factory_id',
        'Serial No': 'serial_no',
        'Date ID': 'date_id',
        'Manufactured Date': 'manufactured_date',
        'Customer Field': 'customer_field',
        'License Points Consumed': 'license_points_consumed',
        'Alarm Status': 'alarm_status',
        'Aggregated Alarm Status': 'Aggregated_alarm_status'
    }

    inserted_count = 0
    try:
        for row in csv_reader:
            # Prepare data using the mapping
            inventory_data = {}
            for csv_header, model_field in header_mapping.items():
                # Sanitize data and handle missing headers gracefully
                value = row.get(csv_header, '').strip()
                if not value:
                    value = None
                inventory_data[model_field] = value

            # Convert integers
            inventory_data['slot_id'] = int(inventory_data.get('slot_id') or 0)
            inventory_data['port_id'] = int(inventory_data.get('port_id') or 0)

            db_obj = Inventory(**inventory_data)
            db.add(db_obj)
            inserted_count += 1

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error during CSV upload: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during CSV processing: {e}")

    return {"inserted_count": inserted_count}