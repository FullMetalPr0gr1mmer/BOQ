import csv
from io import StringIO
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy.orm import Session
import io
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload

from Models.RAN.RANInventory import RANInventory
from Models.RAN.RANLvl3 import RANLvl3
from Models.Admin.User import UserProjectAccess, User
from APIs.Core import safe_int, get_db, get_current_user
from Models.RAN.RAN_LLD import RAN_LLD
from Schemas.RAN.RAN_LLDSchema import RANSiteCreate, RANSiteOut, RANSiteUpdate, PaginatedRANSites

ran_lld_router = APIRouter(prefix="/ran-sites", tags=["RAN Sites"])


# --------------------------------------------------------------------------------
# Access Control Helper Functions
# --------------------------------------------------------------------------------

def check_ranlld_project_access(current_user: User, pid_po: str, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project for RAN LLD operations.
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


def get_accessible_projects_for_lld(current_user: User, db: Session):
    """
    Get all project IDs that the current user has access to for RAN LLD operations.
    """
    if current_user.role.name == "senior_admin":
        return None  # Senior admin can access all projects

    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    return [access.Ranproject_id for access in user_accesses]


def get_service_type_name(service_types):
    """Helper function to convert service type codes to names."""
    if not service_types:
        return ""
    type_mapping = {"1": "Software", "2": "Hardware", "3": "Service"}
    return ", ".join([type_mapping.get(str(st).strip(), str(st).strip()) for st in service_types])


# --------------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------------

@ran_lld_router.post("/", response_model=RANSiteOut)
def create_ran_site(
        site: RANSiteCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new RAN Site record.
    """
    # Check if user has edit permission for the project (if pid_po is provided)
    if site.pid_po:
        if not check_ranlld_project_access(current_user, site.pid_po, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create RAN Site records for this project. Contact the Senior Admin."
            )

    # Users cannot create records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to create RAN Site records. Contact the Senior Admin."
        )

    try:
        db_site = RAN_LLD(**site.dict())
        db.add(db_site)
        db.commit()
        db.refresh(db_site)
        return db_site
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating RAN Site record: {str(e)}"
        )


@ran_lld_router.get("", response_model=PaginatedRANSites)
def get_ran_sites(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        search: str = Query(None, min_length=1),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all RAN Sites accessible to the current user with pagination and search.
    """
    try:
        query = db.query(RAN_LLD)

        # Filter by accessible projects if not senior admin
        accessible_projects = get_accessible_projects_for_lld(current_user, db)
        if accessible_projects is not None:
            if not accessible_projects:  # Empty list means no access
                return {"records": [], "total": 0}
            query = query.filter(RAN_LLD.pid_po.in_(accessible_projects))

        if search:
            # Search by site_id and technical_boq
            query = query.filter(
                RAN_LLD.site_id.ilike(f"%{search}%") |
                RAN_LLD.technical_boq.ilike(f"%{search}%")
            )

        total = query.count()
        sites = query.order_by(RAN_LLD.id).offset(skip).limit(limit).all()

        return {"records": sites, "total": total}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving RAN Sites: {str(e)}"
        )


@ran_lld_router.get("/{site_id}", response_model=RANSiteOut)
def get_ran_site(
        site_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific RAN Site by ID.
    """
    site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="RAN Site not found")

    # Check if user has view permission for the project (if pid_po exists)
    if site.pid_po:
        if not check_ranlld_project_access(current_user, site.pid_po, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this RAN Site record. Contact the Senior Admin."
            )

    return site


@ran_lld_router.put("/{site_id}", response_model=RANSiteOut)
def update_ran_site(
        site_id: int,
        site: RANSiteUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update an existing RAN Site record.
    """
    # First check if record exists
    db_site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not db_site:
        raise HTTPException(status_code=404, detail="RAN Site not found")

    # Check if user has edit permission for the project (if pid_po exists)
    if db_site.pid_po:
        if not check_ranlld_project_access(current_user, db_site.pid_po, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this RAN Site record. Contact the Senior Admin."
            )

    # Users cannot update records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to update RAN Site records. Contact the Senior Admin."
        )

    try:
        for key, value in site.dict().items():
            setattr(db_site, key, value)

        db.commit()
        db.refresh(db_site)
        return db_site
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating RAN Site record: {str(e)}"
        )


@ran_lld_router.delete("/{site_id}")
def delete_ran_site(
        site_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a RAN Site record by ID.
    """
    # First check if record exists
    db_site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not db_site:
        raise HTTPException(status_code=404, detail="RAN Site not found")

    # Check if user has all permission for the project (required for deletion)
    if db_site.pid_po:
        if not check_ranlld_project_access(current_user, db_site.pid_po, db, "all"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this RAN Site record. Contact the Senior Admin."
            )

    # Users cannot delete records
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to delete RAN Site records. Contact the Senior Admin."
        )

    try:
        db.delete(db_site)
        db.commit()
        return {"detail": "RAN Site deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting RAN Site record: {str(e)}"
        )


@ran_lld_router.post("/upload-csv")
def upload_csv(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload CSV file to bulk-add RAN Site records.
    """
    # Users cannot upload CSV files
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to upload CSV files. Contact the Senior Admin."
        )

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    try:
        content = file.file.read().decode("utf-8")
        reader = csv.DictReader(StringIO(content))
        inserted_count = 0

        for row in reader:
            pid_po = row.get("pid_po")

            # Check access for each record's project if pid_po is provided
            if pid_po and not check_ranlld_project_access(current_user, pid_po, db, "edit"):
                continue  # Skip records for projects the user doesn't have access to

            site = RAN_LLD(
                site_id=row.get("Site ID"),
                new_antennas=row.get("New Antennas"),
                total_antennas=safe_int(row.get("Total Antennas", 0)),
                technical_boq=row.get("Technical BoQ"),
                key=row.get("Technical BoQ Key"),
                pid_po=pid_po,
            )
            db.add(site)
            inserted_count += 1

        db.commit()
        return {"inserted": inserted_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading CSV: {str(e)}"
        )


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
        "PO Line -L1","UPL line","Merge POLine# UPLLine#","Item Code","L1 Category", "Service Type", "Seq.-L2",
        "Model Name / Description", "Serial number", "Quantity", "Notes"
    ]
    writer.writerow(headers)

    # Write data rows from matching parents and their children
    for parent in matching_parents:
        parent_row = [
            parent.po_line,
            parent_row.upl_line or "NA",
            parent.po_line + "-" + parent_row.upl_line ,
            "NA",  # Item Code
            parent.category,
            get_service_type_name(parent.service_type),
            "NA",
            parent.item_name,  # Model Name / Description
            "NA",  # Serial number for parents is always NA
            1,#parent.total_quantity if parent.total_quantity is not None else 0,
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
                    parent.po_line or "NA",
                    child_row.upl_line or "NA",
                    parent.po_line + "-" + child_row.upl_line ,
                    child.vendor_part_number,
                    child.category or "NA",
                    get_service_type_name(parent.service_type),
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
                    "NA","NA","NA","NA", "NA", "NA", "NA",
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
