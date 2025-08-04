from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from APIs.Core import get_db, get_current_user
from Models.Site import Site
from Models.Inventory import  Inventory
from Schemas.InventoySchema import AddSite, CreateInventory

inventoryRoute=APIRouter(tags=["Inventory/Sites"])

@inventoryRoute.post("/add-site")
def add_site(site_data: AddSite, db: Session = Depends(get_db)): # Renamed input for clarity
    # Check if a site with this ID already exists
    existing_site = db.query(Site).filter(Site.site_id == site_data.site_id).first()
    # If a site was found in the DB, raise an error
    if existing_site:
        raise HTTPException(status_code=400, detail="Site already exists")

    # If no site exists, create a new one using the original 'site_data'
    new_site_db = Site(site_id=site_data.site_id,
                       site_name=site_data.site_name,
                       project_id=site_data.pid_po)


    db.add(new_site_db)
    db.commit()
    db.refresh(new_site_db)
    return new_site_db# Use POST for creating new data

@inventoryRoute.get("/get-site")
def get_sites(db: Session = Depends(get_db)):
    return db.query(Site).all()




@inventoryRoute.post("/create-inventory")
# Renamed the input variable to avoid conflict
def create_inventory(inventory_data: CreateInventory,
                    # current_user:dict = Depends(get_current_user),
                     db: Session = Depends(get_db)):

    # 1. First, check if the site exists.
    site = db.query(Site).filter(Site.site_id == inventory_data.site_id).first()
    if not site:
        raise HTTPException(status_code=404,  # Use 404 for "Not Found"
                            detail="Site not found. Please add the site first.")

    # 2. Create the new inventory object using the original request data.
    new_inventory = Inventory(
        site_id=inventory_data.site_id,
        site_name=inventory_data.site_name,
        slot_id=inventory_data.slot_id,
        port_id=inventory_data.port_id,
        status=inventory_data.status,
        company_id=inventory_data.company_id,
        mnemonic=inventory_data.mnemonic,
        clei_code=inventory_data.clei_code,
        part_no=inventory_data.part_no,
        software_no=inventory_data.software_no,
        factory_id=inventory_data.factory_id,
        serial_no=inventory_data.serial_no,
        date_id=inventory_data.date_id,
        # Fixed typo here: manufactuEd_date
        manufactured_date=inventory_data.manufactured_date,
        customer_field=inventory_data.customer_field,
        license_points_consumed=inventory_data.license_points_consumed,
        alarm_status=inventory_data.alarm_status,
        Aggregated_alarm_status=inventory_data.Aggregated_alarm_status
    )
    db.add(new_inventory)
    db.commit()
    db.refresh(new_inventory)
    return new_inventory
@inventoryRoute.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    return db.query(Inventory).all()