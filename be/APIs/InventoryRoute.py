# APIs/InventoryRoutes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from APIs.Core import get_db
from Models.Site import Site
from Models.Inventory import Inventory
from Schemas.InventoySchema import AddSite, CreateInventory

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

@inventoryRoute.post("/create-inventory")
def create_inventory(inventory_data: CreateInventory, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.site_id == inventory_data.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found. Please add the site first.")

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


@inventoryRoute.put("/update-inventory/{inventory_id}")
def update_inventory(inventory_id: int, inventory_data: CreateInventory, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    # Only update non-primary fields
    inventory.site_name = inventory_data.site_name
    inventory.slot_id = inventory_data.slot_id
    inventory.port_id = inventory_data.port_id
    inventory.status = inventory_data.status
    inventory.company_id = inventory_data.company_id
    inventory.mnemonic = inventory_data.mnemonic
    inventory.clei_code = inventory_data.clei_code
    inventory.part_no = inventory_data.part_no
    inventory.software_no = inventory_data.software_no
    inventory.factory_id = inventory_data.factory_id
    inventory.serial_no = inventory_data.serial_no
    inventory.date_id = inventory_data.date_id
    inventory.manufactured_date = inventory_data.manufactured_date
    inventory.customer_field = inventory_data.customer_field
    inventory.license_points_consumed = inventory_data.license_points_consumed
    inventory.alarm_status = inventory_data.alarm_status
    inventory.Aggregated_alarm_status = inventory_data.Aggregated_alarm_status

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
