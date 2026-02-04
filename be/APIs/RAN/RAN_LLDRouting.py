import csv
import os
import logging
from io import StringIO
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status, Form, Body
from sqlalchemy.orm import Session
import io
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

# Import PAC generator utility
from utils.pac_generator import create_boq_zip_package

from Models.RAN.RANInventory import RANInventory
from Models.RAN.RANLvl3 import RANLvl3
from Models.RAN.RANAntennaSerials import RANAntennaSerials
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
        limit: int = Query(50, ge=1, le=500),
        search: str = Query(None),
        project_id: str = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all RAN Sites accessible to the current user with pagination and search.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        search: Search term to filter by site_id or technical_boq
        project_id: Filter by specific project ID (pid_po)
    """
    try:
        query = db.query(RAN_LLD)

        # Filter by accessible projects if not senior admin
        accessible_projects = get_accessible_projects_for_lld(current_user, db)
        if accessible_projects is not None:
            if not accessible_projects:  # Empty list means no access
                return {"records": [], "total": 0}
            query = query.filter(RAN_LLD.pid_po.in_(accessible_projects))

        # Filter by specific project if provided
        if project_id:
            # Also check if user has access to this specific project
            if accessible_projects is not None and project_id not in accessible_projects:
                return {"records": [], "total": 0}
            query = query.filter(RAN_LLD.pid_po == project_id)

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
        pid_po: str = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload CSV file to bulk-add RAN Site records.
    The pid_po parameter will be used for all records in the CSV.
    """
    # Check access for the provided project
    if not check_ranlld_project_access(current_user, pid_po, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload CSV files for this project. Contact the Senior Admin."
        )

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    try:
        content = file.file.read().decode("utf-8")
        reader = csv.DictReader(StringIO(content))
        inserted_count = 0

        for row in reader:
            # Try different possible column names for flexibility
            site_id = row.get("Site ID") or row.get("site_id") or row.get("SiteID") or row.get("Site_ID")
            new_antennas = row.get("New Antennas") or row.get("new_antennas") or row.get("NewAntennas") or row.get("New_Antennas")
            total_antennas = row.get("Total Antennas") or row.get("total_antennas") or row.get("TotalAntennas") or row.get("Total_Antennas")
            technical_boq = row.get("Technical BoQ") or row.get("technical_boq") or row.get("TechnicalBoQ") or row.get("Technical_BoQ")
            key = row.get("Technical BoQ Key") or row.get("technical_boq_key") or row.get("TechnicalBoQKey") or row.get("key")

            site = RAN_LLD(
                site_id=site_id,
                new_antennas=new_antennas,
                total_antennas=safe_int(total_antennas, 0),
                technical_boq=technical_boq,
                key=key,
                pid_po=pid_po,  # Use the form parameter for all records
            )
            db.add(site)
            inserted_count += 1

        db.commit()
        return {"inserted": inserted_count, "message": f"Successfully added {inserted_count} RAN Sites with pid_po: {pid_po}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading CSV: {str(e)}"
        )


def _find_matching_serial(child, inventory_pool, used_serials):
    """
    Helper function to find an unused serial number and identification code from the inventory pool
    based on the matching logic.
    Returns a tuple: (serial_number, identification_code)
    """
    if not child.item_details:
        return ("NA", "NA")

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
            identification_code = inv_item.identification_code if hasattr(inv_item, 'identification_code') and inv_item.identification_code else "NA"
            return (inv_item.serial_number, identification_code)

        # 2. First word of child description matches full inventory label
        if child_first_word.lower() == inv_label.lower():
            used_serials.add(inv_item.serial_number)
            identification_code = inv_item.identification_code if hasattr(inv_item, 'identification_code') and inv_item.identification_code else "NA"
            return (inv_item.serial_number, identification_code)

        # 3. First word matches first word
        if child_first_word.lower() == inv_first_word.lower():
            used_serials.add(inv_item.serial_number)
            identification_code = inv_item.identification_code if hasattr(inv_item, 'identification_code') and inv_item.identification_code else "NA"
            return (inv_item.serial_number, identification_code)

    # If no unused serial was found after checking all inventory
    return ("NA", "NA")


# ✅ Generate BoQ CSV from a RAN Site's key (UPDATED LOGIC)
# SECURITY: Added authentication requirement
@ran_lld_router.get("/{site_id}/generate-boq")
def generate_ran_boq(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Fetch the specific RAN Site

    site = db.query(RAN_LLD).filter(RAN_LLD.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not site.key:
        raise HTTPException(status_code=400, detail="Site does not have a key for BoQ generation")

    # Get the project's PO number
    project_po = "NA"
    if site.pid_po:
        from Models.RAN.RANProject import RanProject
        project = db.query(RanProject).filter(RanProject.pid_po == site.pid_po).first()
        if project:
            project_po = project.po or "NA"

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
        "Site ID", "PO#", "PO Line -L1","UPL line","Merge POLine# UPLLine#","Item Code","Sequence","L1 Category", "RAN Category", "Service Type",
        "Model Name / Description", "Serial number", "Identification Code", "Quantity", "Notes"
    ]
    writer.writerow(headers)

    # Write data rows from matching parents and their children
    for parent in matching_parents:
        # Safe concatenation for parent merge line
        po_line_str = str(parent.po_line) if parent.po_line is not None else "NA"
        upl_line_str = str(parent.upl_line) if parent.upl_line is not None else "NA"
        parent_merge_line = f"{po_line_str}\\{upl_line_str}"

        # Determine quantity based on ran_category, service type, and model name
        parent_quantity = 1  # Default quantity
        if (parent.ran_category == "FTK Radio" and
            parent.service_type and "1" in parent.service_type and
            parent.item_name and ("LTE" in parent.item_name or "lte" in parent.item_name)):
            parent_quantity = 3

        parent_row = [
            site.site_id,  # Site ID
            project_po,  # PO#
            parent.po_line,
            parent.upl_line or "NA",
            parent_merge_line,
            "NA",  # Item Code
            parent.sequence or " ",  # Sequence
            parent.category,
            parent.ran_category or "NA",  # RAN Category
            get_service_type_name(parent.service_type),

            parent.item_name,  # Model Name / Description
            "NA",  # Serial number for parents is always NA
            "NA",  # Identification Code for parents is always NA
            parent_quantity,
            "-------------"
        ]
        writer.writerow(parent_row)

        for child in parent.items:
            # ✨ NEW: Repeat child row based on its UOM value (with safe conversion)
            try:
                uom_value = int(child.uom) if child.uom else 0
                repeat_count = uom_value if uom_value > 0 else 1
            except (ValueError, TypeError):
                repeat_count = 1

            for _ in range(repeat_count):
                # ✨ NEW: Find a unique serial number and identification code for this child instance
                serial_to_use, identification_code_to_use = _find_matching_serial(child, inventory_pool, used_serials)

                # Combine Model Name and Description for child
                # Note: Per your schema, the child's description is `item_details`
                description = f"{child.item_details or ''}".strip()

                # Safe concatenation for child merge line
                child_po_line = str(parent.po_line) if parent.po_line is not None else "NA"
                child_upl_line = str(child.upl_line) if child.upl_line is not None else "NA"
                child_merge_line = f"{child_po_line}\\{child_upl_line}"

                child_row = [
                    site.site_id,  # Site ID
                    project_po,  # PO#
                    parent.po_line or "NA",
                    child.upl_line or "NA",
                    child_merge_line,
                    child.vendor_part_number,
                    # parent.sequence or
                    " ",  # Sequence from parent
                    child.category or "NA",
                    parent.ran_category or "NA",  # RAN Category - child takes parent's value
                    get_service_type_name(parent.service_type),

                    description,
                    serial_to_use,  # Use the matched serial number
                    identification_code_to_use,  # Use the matched identification code
                    parent_quantity,  # Quantity takes parent's quantity
                    "-------------"
                ]
                writer.writerow(child_row)

    # ✨ NEW (Step 5): Add New Antennas at the end of the CSV
    if site.new_antennas and site.total_antennas and site.total_antennas > 0:
        try:
            # Search RANLvl3 for matching antenna item to get po_line and upl_line
            antenna_lvl3_item = db.query(RANLvl3).filter(
                RANLvl3.item_name == site.new_antennas
            ).first()

            antenna_po_line = antenna_lvl3_item.po_line if antenna_lvl3_item and antenna_lvl3_item.po_line else "NA"
            antenna_upl_line = antenna_lvl3_item.upl_line if antenna_lvl3_item and antenna_lvl3_item.upl_line else "NA"
            antenna_category = antenna_lvl3_item.category if antenna_lvl3_item and antenna_lvl3_item.category else "NA"
            antenna_ran_category = antenna_lvl3_item.ran_category if antenna_lvl3_item and antenna_lvl3_item.ran_category else "NA"
            antenna_service_type = get_service_type_name(antenna_lvl3_item.service_type) if antenna_lvl3_item and antenna_lvl3_item.service_type else "NA"
            antenna_sequence = antenna_lvl3_item.sequence if antenna_lvl3_item and antenna_lvl3_item.sequence else " "

            # Create merge line for antenna
            antenna_po_line_str = str(antenna_po_line) if antenna_po_line != "NA" else "NA"
            antenna_upl_line_str = str(antenna_upl_line) if antenna_upl_line != "NA" else "NA"
            antenna_merge_line = f"{antenna_po_line_str}\\{antenna_upl_line_str}"

            # Get MRBTS values from inventory pool (already fetched above) for this site
            mrbts_values = set()
            for inv_item in inventory_pool:
                if inv_item.mrbts:
                    mrbts_values.add(inv_item.mrbts)

            # Fetch antenna serials filtered by MRBTS values
            antenna_serials_pool = []
            if mrbts_values:
                antenna_serials_pool = db.query(RANAntennaSerials).filter(
                    RANAntennaSerials.mrbts.in_(mrbts_values)
                ).all()

            used_antenna_serials = set()

            # Ensure total_antennas is a valid integer
            antenna_count = int(site.total_antennas)
            for _ in range(antenna_count):
                # Find an unused serial number
                serial_to_use = "XXXXXXXX"  # Default if no serial found
                for antenna_serial in antenna_serials_pool:
                    if antenna_serial.serial_number and antenna_serial.serial_number not in used_antenna_serials:
                        serial_to_use = antenna_serial.serial_number
                        used_antenna_serials.add(antenna_serial.serial_number)
                        break

                antenna_row = [
                    site.site_id,  # Site ID
                    project_po,  # PO#
                    antenna_po_line,  # PO Line from RANLvl3
                    antenna_upl_line,  # UPL Line from RANLvl3
                    antenna_merge_line,  # Merge line
                    "NA",  # Item Code
                    antenna_sequence,  # Sequence from RANLvl3
                    antenna_category,  # L1 Category from RANLvl3
                    antenna_ran_category,  # RAN Category from RANLvl3
                    antenna_service_type,  # Service Type from RANLvl3
                    site.new_antennas,  # Model Name / Description
                    serial_to_use,  # Serial Number
                    "NA",  # Identification Code (antennas don't use inventory items)
                    1,  # Quantity
                    "-------------"  # Notes
                ]
                writer.writerow(antenna_row)
        except (ValueError, TypeError):
            # Handle cases where total_antennas is not a valid number
            pass

    output.seek(0)
    csv_content = output.getvalue()

    # Return plain CSV content (text)
    return csv_content


@ran_lld_router.post("/download-zip")
def download_ran_boq_zip(
        payload: Dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Download RAN BOQ as ZIP file containing CSV and PAC Word document.

    Expected payload:
    - csv_content: The CSV content (potentially edited by user)
    - site_id: The RAN site ID (database ID, not site_id field)
    """
    try:
        csv_content = payload.get("csv_content")
        site_db_id = payload.get("site_id")

        if not csv_content:
            raise HTTPException(status_code=400, detail="csv_content is required")
        if not site_db_id:
            raise HTTPException(status_code=400, detail="site_id is required")

        # 1. Get site info
        site = db.query(RAN_LLD).filter(RAN_LLD.id == site_db_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        # 2. Get project info
        from Models.RAN.RANProject import RanProject
        project = db.query(RanProject).filter(RanProject.pid_po == site.pid_po).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 3. Check access
        if not check_ranlld_project_access(current_user, site.pid_po, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to download BOQ for this project."
            )

        # 4. Get template path
        template_path = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "PAC_Template.docx")

        # 4.5. Extract model name and PO line number from "Implementation services" row
        model_name = "Implementation services - New Site"  # Default fallback
        po_line_number_str = "1"  # Default fallback

        try:
            import csv
            from io import StringIO

            csv_reader = csv.DictReader(StringIO(csv_content))

            for row in csv_reader:
                # Look for row with "Implementation services" in Model Name column
                # Try both possible header formats (with and without space after "Name")
                model_col = row.get('Model Name / Description', '').strip()
                if not model_col:
                    model_col = row.get('Model Name/Description', '').strip()

                if 'Implementation services' in model_col:
                    model_name = model_col
                    po_line = row.get('PO Line -L1', '').strip()
                    if po_line:
                        po_line_number_str = po_line
                    break
        except Exception:
            # Use default values if extraction fails
            pass

        # 5. Generate ZIP package
        zip_buffer = create_boq_zip_package(
            csv_content=csv_content,
            site_id=site.site_id,
            project_name=project.project_name,
            project_po=project.pid_po,
            link_id=site.site_id,  # Use site_id as link_id for certificate number
            template_path=template_path,
            csv_filename=f"RAN_BOQ_{site.site_id}.csv",
            po_line_number=po_line_number_str,
            model_name=model_name
        )

        # 6. Return ZIP file as download
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=RAN_BOQ_{site.site_id}.zip"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ZIP package: {str(e)}")


@ran_lld_router.delete("/delete-all-sites/{pid_po}")
def delete_all_ran_sites_for_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes all RAN LLD sites for a project.
    Users need 'all' permission on the project to delete all sites.

    Returns:
    - deleted_sites: Number of RAN sites deleted
    - affected_tables: List of tables that had data deleted
    """
    # Check user has 'all' permission
    if not check_ranlld_project_access(current_user, pid_po, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete RAN sites for this project."
        )

    try:
        # Get count of sites for this project
        sites_count = db.query(RAN_LLD).filter(RAN_LLD.pid_po == pid_po).count()

        if sites_count == 0:
            raise HTTPException(status_code=404, detail="No RAN sites found for this project")

        # Delete all RAN sites for this project
        sites_deleted = db.query(RAN_LLD).filter(RAN_LLD.pid_po == pid_po).delete(synchronize_session=False)

        db.commit()

        return {
            "message": "All RAN sites deleted successfully",
            "deleted_sites": sites_deleted,
            "affected_tables": ["ran_lld"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete RAN sites: {str(e)}")
