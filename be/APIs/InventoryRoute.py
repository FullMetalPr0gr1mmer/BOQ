from fastapi import APIRouter

from Models.Inventory import Inventory
from Schemas.InventoySchema import CreateInventory, InventoryOut, InventoryPagination, SitesResponse, UploadResponse

inventoryRoute = APIRouter(tags=["Inventory/Sites"])

# ----------------------------
# SITE CRUD
# ----------------------------
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import csv
from io import StringIO

from APIs.Core import get_db
from Models.Site import Site
from Schemas.InventoySchema import AddSite
from pydantic import BaseModel

inventoryRoute = APIRouter(tags=["Inventory/Sites"])



# ----------------------------
# SITE CRUD with Pagination & Search
# ----------------------------

@inventoryRoute.post("/add-site", response_model=AddSite)
def add_site(site_data: AddSite, db: Session = Depends(get_db)):
    """
    Adds a new site to the database.
    """
    existing_site = db.query(Site).filter(Site.site_id == site_data.site_id).first()
    if existing_site:
        raise HTTPException(status_code=400, detail="Site with this ID already exists")

    new_site = Site(
        site_id=site_data.site_id,
        site_name=site_data.site_name,
        project_id=site_data.pid_po
    )
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    return AddSite(
        site_id=new_site.site_id,
        site_name=new_site.site_name,
        pid_po=new_site.project_id
    )


@inventoryRoute.get("/sites", response_model=SitesResponse)
def get_sites_paginated(
        db: Session = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        search: Optional[str] = Query(None)
):
    """
    Retrieves a paginated list of sites with optional search functionality.
    """
    query = db.query(Site)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Site.site_id.ilike(search_pattern),
                Site.site_name.ilike(search_pattern),
                Site.project_id.ilike(search_pattern)
            )
        )

    total_count = query.count()
    sites = query.order_by(Site.site_id).offset(skip).limit(limit).all()
    records = [
        AddSite(
            site_id=site.site_id,
            site_name=site.site_name,
            pid_po=site.project_id
        ) for site in sites
    ]

    return SitesResponse(records=records, total=total_count)


@inventoryRoute.put("/update-site/{site_id}", response_model=AddSite)
def update_site(site_id: str, site_data: AddSite, db: Session = Depends(get_db)):
    """
    Updates the details of an existing site.
    Note: site_id cannot be changed.
    """
    site = db.query(Site).filter(Site.site_id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Update only the allowed fields
    site.site_name = site_data.site_name
    site.project_id = site_data.pid_po
    db.commit()
    db.refresh(site)

    return AddSite(
        site_id=site.site_id,
        site_name=site.site_name,
        pid_po=site.project_id
    )


@inventoryRoute.delete("/delete-site/{site_id}")
def delete_site(site_id: str, db: Session = Depends(get_db)):
    """
    Deletes a site from the database.
    """
    site = db.query(Site).filter(Site.site_id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    db.delete(site)
    db.commit()
    return {"message": f"Site {site_id} deleted successfully"}


@inventoryRoute.post("/sites/upload-csv", response_model=UploadResponse)
async def upload_sites_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads a CSV file and creates sites based on the link data.
    Expected CSV format: linkid, InterfaceName, SiteIPA, SiteIPB
    Example: JIZ0243-JIZ0169, Port 3/5-Port 3/5, 10.10.158.228, 10.10.158.227

    This will create:
    - Site: JIZ0243 with site_id: 10.10.158.228, project_id: "00"
    - Site: JIZ0169 with site_id: 10.10.158.227, project_id: "00"
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()
        csv_content = StringIO(content.decode('utf-8'))
        csv_reader = csv.reader(csv_content)

        # Skip header row if present
        first_row = next(csv_reader, None)
        if first_row and any(header.lower() in ['linkid', 'interfacename', 'siteipa', 'siteipb']
                             for header in first_row):
            # This was a header row, continue processing
            pass
        else:
            # This wasn't a header row, reset reader to include first row
            csv_content.seek(0)
            csv_reader = csv.reader(csv_content)

        inserted_count = 0
        processed_sites = set()  # To avoid duplicates

        for row in csv_reader:
            if len(row) < 4:
                continue  # Skip malformed rows

            linkid = row[0].strip()
            interface_name = row[1].strip()
            site_ipa = row[2].strip()
            site_ipb = row[3].strip()

            # Parse linkid (e.g., "JIZ0243-JIZ0169")
            if '-' not in linkid:
                continue  # Skip if linkid doesn't contain separator

            site_names = linkid.split('-')
            if len(site_names) != 2:
                continue  # Skip if not exactly 2 sites

            site_name_a = site_names[0].strip()
            site_name_b = site_names[1].strip()

            # Create or update site A
            site_a_key = (site_name_a, site_ipa)
            if site_a_key not in processed_sites:
                existing_site_a = db.query(Site).filter(Site.site_id == site_ipa).first()
                if not existing_site_a:
                    new_site_a = Site(
                        site_id=site_ipa,
                        site_name=site_name_a,
                        project_id="SophiaSophia"
                    )
                    db.add(new_site_a)
                    inserted_count += 1
                processed_sites.add(site_a_key)

            # Create or update site B
            site_b_key = (site_name_b, site_ipb)
            if site_b_key not in processed_sites:
                existing_site_b = db.query(Site).filter(Site.site_id == site_ipb).first()
                if not existing_site_b:
                    new_site_b = Site(
                        site_id=site_ipb,
                        site_name=site_name_b,
                        project_id="SophiaSophia"
                    )
                    db.add(new_site_b)
                    inserted_count += 1
                processed_sites.add(site_b_key)

        db.commit()

        return UploadResponse(
            inserted=inserted_count,
            message=f"Successfully processed CSV and inserted {inserted_count} new sites"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


# Keep the legacy endpoint for backward compatibility
@inventoryRoute.get("/get-site")
def get_all_sites_legacy(db: Session = Depends(get_db)):
    """
    Legacy endpoint - returns all sites without pagination.
    Use /sites for paginated results.
    """
    sites = db.query(Site).all()
    return [
        {
            "site_id": site.site_id,
            "site_name": site.site_name,
            "project_id": site.project_id
        } for site in sites
    ]
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