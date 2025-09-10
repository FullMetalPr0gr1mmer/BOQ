import csv
from io import StringIO
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
import io
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload

from Models.RAN.RANInventory import RANInventory
from Models.RAN.RANLvl3 import RANLvl3
from APIs.Core import get_db, safe_int
from Models.RAN.RAN_LLD import RAN_LLD
from Schemas.RAN.RAN_LLDSchema import RANSiteCreate, RANSiteOut, RANSiteUpdate, PaginatedRANSites

ran_lld_router = APIRouter(prefix="/ran-sites", tags=["RAN Sites"])



# ✅ Create
@ran_lld_router.post("/", response_model=RANSiteOut)
def create_ran_site(site: RANSiteCreate, db: Session = Depends(get_db)):
    db_site = RAN_LLD(**site.dict())
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site


@ran_lld_router.get("/", response_model=PaginatedRANSites)
def get_ran_sites(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        search: str = Query(None, min_length=1),
        db: Session = Depends(get_db),
):
    query = db.query(RAN_LLD)

    if search:
        # Assuming you want to search by site_id and technical_boq
        query = query.filter(
            RAN_LLD.site_id.ilike(f"%{search}%") |
            RAN_LLD.technical_boq.ilike(f"%{search}%")
        )

    total = query.count()
    sites = query.order_by(RAN_LLD.id).offset(skip).limit(limit).all()

    return {"records": sites, "total": total}


# ✅ Read by ID
@ran_lld_router.get("/{site_id}", response_model=RANSiteOut)
def get_ran_site(site_id: int, db: Session = Depends(get_db)):
    site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


# ✅ Update
@ran_lld_router.put("/{site_id}", response_model=RANSiteOut)
def update_ran_site(site_id: int, site: RANSiteUpdate, db: Session = Depends(get_db)):
    db_site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not db_site:
        raise HTTPException(status_code=404, detail="Site not found")

    for key, value in site.dict().items():
        setattr(db_site, key, value)

    db.commit()
    db.refresh(db_site)
    return db_site


# ✅ Delete
@ran_lld_router.delete("/{site_id}")
def delete_ran_site(site_id: int, db: Session = Depends(get_db)):
    db_site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not db_site:
        raise HTTPException(status_code=404, detail="Site not found")

    db.delete(db_site)
    db.commit()
    return {"detail": "Site deleted successfully"}


# ✅ Upload CSV
@ran_lld_router.post("/upload-csv")
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    i=0
    for row in reader:

        site = RAN_LLD(
            site_id=row.get("Site ID"),
            new_antennas=row.get("New Antennas"),
            total_antennas=safe_int(row.get("Total Antennas", 0)),
            technical_boq=row.get("Technical BoQ"),
            key=row.get("Technical BoQ Key"),
        )
        db.add(site)
        i=i+1
    db.commit()
    return {"inserted":i}


# @ran_lld_router.get("/{site_id}/generate-boq")
# def generate_ran_boq(site_id: int, db: Session = Depends(get_db)):
#     """
#     Generates a Bill of Quantities (BoQ) CSV file based on the site's 'key'.
#     1. Fetches the RAN Site by its ID.
#     2. Parses the site's 'key' attribute (e.g., "4,5,12") into a set of numbers.
#     3. Fetches all RANLvl3 parent items that have any of those numbers in their own 'key'.
#     4. Constructs a CSV file with details from the matching parents and their children.
#     5. Returns the CSV file as a download.
#     """
#     # 1. Fetch the specific RAN Site
#     site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
#     if not site:
#         raise HTTPException(status_code=404, detail="Site not found")
#     if not site.key:
#         raise HTTPException(status_code=400, detail="Site does not have a key for BoQ generation")
#
#     # 2. Parse the site's key into a set of unique strings for matching
#     try:
#         keys_to_find = {k.strip() for k in site.key.split(',') if k.strip()}
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid key format in site data")
#
#     # 3. Fetch all RANLvl3 parents with their children (items) eagerly loaded
#     all_parents = db.query(RANLvl3).options(joinedload(RANLvl3.items)).all()
#
#     matching_parents = []
#     for parent in all_parents:
#         if parent.key:
#             parent_keys = {pk.strip() for pk in parent.key.split(',')}
#             # Check if there is any intersection between the two sets of keys
#             if not keys_to_find.isdisjoint(parent_keys):
#                 matching_parents.append(parent)
#
#     if not matching_parents:
#         raise HTTPException(status_code=404, detail="No matching BoQ items found for the given key")
#
#     # 4. Construct the CSV data in memory
#     output = io.StringIO()
#     writer = csv.writer(output)
#
#     # Write CSV headers
#     headers = [
#         "PO Line -L1", "Item Code", "Merge POLine#UPLLine#", "Seq.-L2",
#         "Model Name/Description", "Serial number", "Quantity", "Notes"
#     ]
#     writer.writerow(headers)
#
#     # Write data rows from matching parents and their children
#     for parent in matching_parents:
#         # Add a row for the parent item
#
#         parent_row = [
#             "NA",  # PO Line -L1
#             "",  # Item Code (parents don't have vendor_part_number)
#             "NA",  # Merge POLine#UPLLine#
#             "NA",  # Seq.-L2
#             parent.item_name,  # Model Name  # Description
#             "NA",  # Serial number
#             parent.total_quantity if parent.total_quantity is not None else 0,  # Quantity
#             ""  # Notes
#         ]
#         writer.writerow(parent_row)
#         for child in parent.items:
#             child_row = [
#                 "NA",  # PO Line -L1
#                 child.vendor_part_number,  # Item Code
#                 "NA",  # Merge POLine#UPLLine#
#                 "NA",  # Seq.-L2  # Model Name
#                 child.item_details,  # Description
#                 "NA",  # Serial number
#                 child.quantity if child.quantity is not None else 0,  # Quantity
#                 ""  # Notes
#             ]
#             writer.writerow(child_row)
#
#
#         # Add rows for each child item
#
#
#     output.seek(0)
#
#     # 5. Return the CSV as a streaming response for download
#     return StreamingResponse(
#         output,
#         media_type="text/csv",
#         headers={"Content-Disposition": f"attachment; filename=boq_{site.site_id}.csv"}
#     )
#


def _find_matching_serial(child, inventory_pool, used_serials):
    """
    Helper function to find an unused serial number from the inventory pool
    based on the matching logic.
    """
    if not child.item_details:
        return "NA"

    # Prepare match strings from the child's description
    child_description = child.item_details.strip()
    child_first_word = child_description.split()[0] if ' ' in child_description else child_description

    # Iterate through available inventory to find a match
    for inv_item in inventory_pool:
        # Skip if serial is missing or already used
        if not inv_item.serial_number or inv_item.serial_number in used_serials:
            continue

        if not inv_item.user_label:
            continue

        # Prepare match strings from the inventory item's user label
        inv_label = inv_item.user_label.strip()
        inv_first_word = inv_label.split()[0] if ' ' in inv_label else inv_label

        # --- Matching Logic ---
        # 1. Exact match on full description
        if child_description.lower() == inv_label.lower():
            used_serials.add(inv_item.serial_number)
            return inv_item.serial_number

        # 2. First word of child description matches full inventory label
        if child_first_word.lower() == inv_label.lower():
            used_serials.add(inv_item.serial_number)
            return inv_item.serial_number

        # 3. First word matches first word
        if child_first_word.lower() == inv_first_word.lower():
            used_serials.add(inv_item.serial_number)
            return inv_item.serial_number

    # If no unused serial was found after checking all inventory
    return "NA"


# ✅ Generate BoQ CSV from a RAN Site's key (UPDATED LOGIC)
@ran_lld_router.get("/{site_id}/generate-boq")
def generate_ran_boq(site_id: int, db: Session = Depends(get_db)):
    # 1. Fetch the specific RAN Site
    site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not site.key:
        raise HTTPException(status_code=400, detail="Site does not have a key for BoQ generation")

    # ✨ NEW: Fetch all inventory records for the site's site_id
    inventory_pool = db.query(RANInventory).filter(RANInventory.site_id == site.site_id).all()
    used_serials = set()

    # 2. Parse the site's key
    try:
        keys_to_find = {k.strip() for k in site.key.split(',') if k.strip()}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid key format in site data")

    # 3. Fetch matching RANLvl3 parents and their children
    all_parents = db.query(RANLvl3).options(joinedload(RANLvl3.items)).all()
    matching_parents = []
    for parent in all_parents:
        if parent.key:
            parent_keys = {pk.strip() for pk in parent.key.split(',')}
            if not keys_to_find.isdisjoint(parent_keys):
                matching_parents.append(parent)

    if not matching_parents:
        raise HTTPException(status_code=404, detail="No matching BoQ items found for the given key")

    # 4. Construct the CSV data in memory
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "PO Line -L1", "Item Code", "Merge POLine#UPLLine#", "Seq.-L2",
        "Model Name / Description", "Serial number", "Quantity", "Notes"
    ]
    writer.writerow(headers)

    # Write data rows from matching parents and their children
    for parent in matching_parents:
        parent_row = [
            "NA",
            "NA",  # Item Code
            "NA",
            "NA",
            parent.item_name,  # Model Name / Description
            "NA",  # Serial number for parents is always NA
            parent.total_quantity if parent.total_quantity is not None else 0,
            "-------------"
        ]
        writer.writerow(parent_row)

        for child in parent.items:
            # ✨ NEW: Repeat child row based on its UOM value
            repeat_count = int(child.uom) if child.uom and int(child.uom) > 0 else 1
            for _ in range(repeat_count):
                # ✨ NEW: Find a unique serial number for this child instance
                serial_to_use = _find_matching_serial(child, inventory_pool, used_serials)

                # Combine Model Name and Description for child
                # Note: Per your schema, the child's description is `item_details`
                description = f"{child.item_details or ''}".strip()

                child_row = [
                    "NA",
                    child.vendor_part_number,
                    "NA",
                    "NA",
                    description,
                    serial_to_use,  # Use the matched serial number
                    1,  # Quantity is 1 because we are repeating the row
                    "-------------"
                ]
                writer.writerow(child_row)

    # ✨ NEW (Step 5): Add New Antennas at the end of the CSV
    if site.new_antennas and site.total_antennas and site.total_antennas > 0:
        try:
            # Ensure total_antennas is a valid integer
            antenna_count = int(site.total_antennas)
            for _ in range(antenna_count):
                antenna_row = [
                    "NA", "NA", "NA", "NA",
                    site.new_antennas,  # Model Name / Description
                    "XXXXXXXX",  # Serial Number
                    1,  # Quantity
                    "-------------"  # Notes
                ]
                writer.writerow(antenna_row)
        except (ValueError, TypeError):
            # Handle cases where total_antennas is not a valid number
            pass

    output.seek(0)

    # 5. Return the CSV as a streaming response
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=boq_{site.site_id}.csv"}
    )
