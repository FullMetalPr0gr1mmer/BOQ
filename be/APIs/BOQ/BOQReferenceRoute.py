from typing import Optional, List, Tuple, Dict, Any, Union
import csv
import datetime
import os
from io import StringIO

from fastapi import UploadFile, File, status, Query, HTTPException, Depends, Body, APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, func, and_
from sqlalchemy.orm import Session

# Import PAC generator utility
from utils.pac_generator import create_boq_zip_package

# Core and Schema Imports
from APIs.Core import _parse_interface_name, _sa_row_to_dict, get_db, get_current_user
from Schemas.BOQ.BOQReferenceSchema import BOQReferenceOut, BOQReferenceCreate

# Model Imports
from Models.BOQ.LLD import LLD
from Models.BOQ.Levels import Lvl3
from Models.BOQ.Inventory import Inventory
from Models.BOQ.BOQReference import BOQReference
from Models.BOQ.Site import Site
from Models.BOQ.Dismantling import Dismantling
from Models.BOQ.Project import Project
from Models.Admin.User import User, UserProjectAccess

# Project Route for get_project_for_boq helper
from APIs.BOQ.ProjectRoute import get_project_for_boq

BOQRouter = APIRouter(prefix="/boq", tags=["BOQ Generation"])
EXPECTED_HEADERS = ["linkid", "InterfaceName", "SiteIPA", "SiteIPB"]


# --- ADMINISTRATION & ACCESS CONTROL HELPERS ---
# NOTE: For better code organization, these helpers could be moved to a shared 'auth_utils.py' file.

def check_project_access(current_user: User, project: Project, db: Session, required_permission: str = "view"):
    """
    Helper function to check if a user has access to a project with the required permission level.
    """
    if not project:
        return False  # No project, no access.
    if current_user.role.name == "senior_admin":
        return True

    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == project.pid_po
    ).first()

    if not access:
        return False

    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }
    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_project_ids(current_user: User, db: Session) -> List[str]:
    """
    Returns a list of project IDs (pid_po) that the current user has access to.
    """
    if current_user.role.name == "senior_admin":
        return [p.pid_po for p in db.query(Project.pid_po).all()]

    return [
        access.project_id for access in db.query(UserProjectAccess.project_id).filter(
            UserProjectAccess.user_id == current_user.id
        ).all()
    ]


# --- CRUD AND FILE PROCESSING ENDPOINTS ---

@BOQRouter.post("/upload-reference", response_model=Dict[str, int], status_code=status.HTTP_201_CREATED)
async def upload_reference_csv(
        project_id: str = Query(..., description="The Project ID (pid_po) to associate the references with."),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Authorization Check
    project = db.query(Project).filter(Project.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID '{project_id}' not found.")

    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload references for this project."
        )

    # 2. Original CSV Processing Logic
    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="ignore")
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty file")

        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(text)
        except Exception:
            class _Tsv(csv.Dialect):
                delimiter = "\t";
                quotechar = '"';
                escapechar = None
                doublequote = True;
                skipinitialspace = False
                lineterminator = "\n";
                quoting = csv.QUOTE_MINIMAL

            dialect = _Tsv

        reader = csv.DictReader(StringIO(text), dialect=dialect)
        reader.fieldnames = [h.strip().lstrip('\ufeff') for h in (reader.fieldnames or [])]

        missing = [h for h in EXPECTED_HEADERS if h not in reader.fieldnames]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing headers: {missing}. Got: {reader.fieldnames}")

        to_insert, processed = [], 0
        for row in reader:
            processed += 1
            linkid = (row.get("linkid") or "").strip()
            if not linkid:  # Skip rows without a linkid
                continue

            to_insert.append(BOQReference(
                linkid=linkid,
                interface_name=(row.get("InterfaceName") or "").strip() or None,
                site_ip_a=(row.get("SiteIPA") or "").strip() or None,
                site_ip_b=(row.get("SiteIPB") or "").strip() or None,
                pid_po=project_id,  # Associate with the validated project_id
            ))

        if not to_insert:
            raise HTTPException(status_code=400, detail="No valid rows with linkid found")

        db.bulk_save_objects(to_insert)
        db.commit()
        return {"rows_processed": processed, "rows_inserted": len(to_insert)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {e}")


@BOQRouter.get("/references")
def list_references(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        search: Optional[str] = Query(None, description="Filter by linkid/interface/site IP (case-insensitive)"),
        project_id: Optional[str] = Query(None, description="Filter by specific project ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Get accessible project IDs
    accessible_project_ids = get_user_accessible_project_ids(current_user, db)
    if not accessible_project_ids:
        return {"total": 0, "items": []}

    # 2. Base query filtered by user's projects
    q = db.query(BOQReference).filter(BOQReference.pid_po.in_(accessible_project_ids))

    # 3. Apply project filter if specified
    if project_id:
        # Verify user has access to this specific project
        if project_id not in accessible_project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project."
            )
        q = q.filter(BOQReference.pid_po == project_id)

    # 4. Apply search filter
    if search:
        s = f"%{search.strip().lower()}%"
        q = q.filter(or_(
            func.lower(func.coalesce(BOQReference.linkid, "")).like(s),
            func.lower(func.coalesce(BOQReference.interface_name, "")).like(s),
            func.lower(func.coalesce(BOQReference.site_ip_a, "")).like(s),
            func.lower(func.coalesce(BOQReference.site_ip_b, "")).like(s),
        ))

    total = q.count()
    rows = q.order_by(BOQReference.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [BOQReferenceOut.model_validate(r).model_dump(by_alias=True) for r in rows]
    }


@BOQRouter.post("/reference", response_model=BOQReferenceOut, status_code=status.HTTP_201_CREATED)
def create_reference(
        payload: BOQReferenceCreate,  # Assuming BOQReferenceCreate schema includes 'pid_po'
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Authorization Check
    project = db.query(Project).filter(Project.pid_po == payload.pid_po).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Project with ID '{payload.pid_po}' not found.")

    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create references for this project."
        )

    # 2. Create Object
    new_ref = BOQReference(**payload.model_dump())
    db.add(new_ref)
    db.commit()
    db.refresh(new_ref)
    return BOQReferenceOut.model_validate(new_ref).model_dump(by_alias=True)


@BOQRouter.get("/reference/{id}", response_model=BOQReferenceOut)
def get_reference(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ref = db.query(BOQReference).filter(BOQReference.id == id).first()
    if not ref:
        raise HTTPException(status_code=404, detail=f"Reference with id '{id}' not found")

    # Authorization Check
    project = db.query(Project).filter(Project.pid_po == ref.pid_po).first()
    if not check_project_access(current_user, project, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this reference."
        )

    return BOQReferenceOut.model_validate(ref).model_dump(by_alias=True)


@BOQRouter.put("/reference/{id}", response_model=BOQReferenceOut)
def update_reference(
        id: str,
        payload: BOQReferenceCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    ref = db.query(BOQReference).filter(BOQReference.id == id).first()
    if not ref:
        raise HTTPException(status_code=404, detail=f"Reference with id '{id}' not found")

    # Authorization Check
    project = db.query(Project).filter(Project.pid_po == ref.pid_po).first()
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this reference."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(ref, key):
            setattr(ref, key, value)

    db.add(ref)
    db.commit()
    db.refresh(ref)
    return BOQReferenceOut.model_validate(ref).model_dump(by_alias=True)


@BOQRouter.delete("/reference/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ref = db.query(BOQReference).filter(BOQReference.id == id).first()
    if not ref:
        raise HTTPException(status_code=404, detail=f"Reference with id '{id}' not found")

    # Authorization Check (Requires "all" permission for deletion)
    project = db.query(Project).filter(Project.pid_po == ref.pid_po).first()
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this reference."
        )

    db.delete(ref)
    db.commit()
    return


# --- BOQ Generation Logic (Unchanged Core Logic, but with added security) ---

# Note: The helper functions 'process_boq_data' and '_generate_site_csv_content'
# do not need security checks themselves as they are called by a secured endpoint.

def process_boq_data(site_a_ip: str, site_b_ip: str, linked_ip: str, db: Session) -> Tuple:
    """Fetch LLD, inventory, and Lvl3 rows, handle swap/dismantling."""

    # Fetch BOQ references
    refs = db.query(BOQReference).filter(
        BOQReference.site_ip_a == site_a_ip,
        BOQReference.site_ip_b == site_b_ip
    ).all()

    # OUTDOOR inventory
    outdoor_inventory_a = []
    outdoor_inventory_b = []
    site_a_serials = set()
    site_b_serials = set()
    for ref in refs:
        parsed = _parse_interface_name(ref.interface_name)

        if ref.site_ip_a and parsed.get("a_slot") is not None and parsed.get("a_port") is not None:
            inv_rows_a = db.query(Inventory).filter(and_(
                Inventory.site_id == ref.site_ip_a,
                Inventory.slot_id == parsed["a_slot"],
                Inventory.port_id == parsed["a_port"])
            ).all()
            # if inv_rows_a.serial_no not in site_a_serials:
            #     site_a_serials.add(inv_rows_a.serial_no)
            outdoor_inventory_a.extend([_sa_row_to_dict(r) for r in inv_rows_a])

        if ref.site_ip_b and parsed.get("b_slot") is not None and parsed.get("b_port") is not None:
            inv_rows_b = db.query(Inventory).filter(and_(
                Inventory.site_id == ref.site_ip_b,
                Inventory.slot_id == parsed["b_slot"],
                Inventory.port_id == parsed["b_port"])
            ).first()
            if inv_rows_b.serial_no not in site_b_serials:
                site_b_serials.add(inv_rows_b.serial_no)
                outdoor_inventory_b.extend([_sa_row_to_dict(inv_rows_b)])
    # INDOOR inventory (slot=0, port=0)
    indoor_inventory_a = [
        _sa_row_to_dict(r) for r in db.query(Inventory).filter(
            Inventory.site_id == site_a_ip,
            Inventory.slot_id == '0',
            Inventory.port_id == '0'
        ).all()
    ]
    indoor_inventory_b = [
        _sa_row_to_dict(r) for r in db.query(Inventory).filter(
            Inventory.site_id == site_b_ip,
            Inventory.slot_id == '0',
            Inventory.port_id == '0'
        ).all()
    ]

    # Fetch LLD row and extra fields
    lld_row = db.query(LLD).filter(LLD.link_id == linked_ip).first()
    lvl3_rows = []
    if lld_row and lld_row.item_name:
        lvl3_rows = db.query(Lvl3).filter(Lvl3.item_name == lld_row.item_name).all()

    # Handle swap action → fetch dismantling Lvl3 rows
    if lld_row and lld_row.action == "swap":
        dismantling_row = db.query(Dismantling).filter(Dismantling.nokia_link_id == linked_ip).first()
        if dismantling_row and dismantling_row.no_of_dismantling:
            count = int(dismantling_row.no_of_dismantling)
            dismantling_lvl3 = db.query(Lvl3).filter(Lvl3.item_name.ilike("%Dismantling%")).all()
            lvl3_rows.extend(dismantling_lvl3 * count)

    # Fetch MW Planning services item and add it to lvl3_rows
    mw_planning_lvl3 = db.query(Lvl3).filter(Lvl3.item_name == "MW Planning services").first()
    if mw_planning_lvl3:
        lvl3_rows.append(mw_planning_lvl3)

    return lvl3_rows, outdoor_inventory_a, indoor_inventory_a, outdoor_inventory_b, indoor_inventory_b, lld_row


def _generate_site_csv_content(site_ip: str, lvl3_rows: List, outdoor_inventory: List[Dict],
                               indoor_inventory: List[Dict], db: Session, lld_row: LLD, site_type: str,
                               code: Optional[str] = None) -> str:
    """Generate CSV content for a site with repeated OUTDOOR/INDOOR items and antenna handling."""
    # ... (original function code is unchanged)
    output = StringIO()
    writer = csv.writer(output)
    if site_type == "A":
        # Fetch site name
        site_name = ""
        try:
            site = db.query(Site).filter(Site.site_id == site_ip).first()
            if site:
                site_name = site.site_name
        except Exception:
            pass
        site_display = f"{site_ip} - {site_name}" if site_name else site_ip

        # Helper to map service types
        def get_service_type_name(service_types):
            if not service_types: return ""
            type_mapping = {"1": "Software", "2": "Hardware", "3": "Service"}
            return ", ".join([type_mapping.get(str(st).strip(), str(st).strip()) for st in service_types])
        try:
            project = get_project_for_boq(lvl3_rows[0].project_id, db=db)
        except Exception:
            pass
        writer.writerow([" ", " ", " ", " ", " "," ", "MW BOQ", " ", " ", " ", " ", " "," ",""])
        writer.writerow(
            ["Project Name:", project.project_name, " ", " ", " ", " "," ", "PO Number:", project.po, " ", " ", " "," "," " ])
        writer.writerow(["Scope:", lld_row.scope, " ", " ", " ", " ", " ", " ", " ", " ", " "," ", " ", ])
        writer.writerow(["MW Code:", code, " ", " ", " ", " "," ", "Region:", lld_row.region," ", " ", " ", " "," " ])

        # CSV Headers
        headers = ["Site_IP", "Item Name", "Item Description", "Sequence", "L1 Category", "Vendor Part Number", "Type", "Category", "UOM",
                   "UPL Line", "Total Qtts", "Discounted unit price", "SN", "SW Number"]
        writer.writerow(headers)

        outdoor_idx = 0
        indoor_idx = 0
        antenna_processed = False  # ✅ Add flag to track if antenna item has been processed
        parents_printed = False
        for lvl3 in lvl3_rows:
            if not parents_printed:
                parents_printed = True
                for parent in lvl3_rows:
                    # Parent row - Item Name = item_name + service type
                    parent_item_name = f"{parent.item_name} ({get_service_type_name(parent.service_type)})" if parent.service_type else parent.item_name
                    writer.writerow([
                        site_display,
                        parent_item_name,  # Item Name column
                        parent.item_name,  # Item Description
                        parent.sequence or " ",  # Sequence
                        "MW links (HW,SW,Services,Passive)",
                        "-----------------",  # Vendor Part Number
                        get_service_type_name(parent.service_type),
                        "MW",
                        "Link",
                        "NA",  # UPL Line - not applicable for parent rows
                        "1",
                        parent.total_price or "",
                        "-----------------",  # SN
                        "-----------------"
                    ])

            for item in lvl3.items:
                item_desc_upper = (item.item_details or item.item_name or "").upper()
                inventory_item = {}

                # Handle OUTDOOR items
                if "OUTDOOR" in item_desc_upper:
                    if outdoor_idx < len(outdoor_inventory):
                        inventory_item = outdoor_inventory[outdoor_idx]
                        outdoor_idx += 1
                    else:
                        continue  # Skip if no inventory left

                    vendor_part = inventory_item.get("part_no", "")
                    serial_no = inventory_item.get("serial_no", "")

                # Handle INDOOR items
                elif "INDOOR" in item_desc_upper:
                    if indoor_idx < len(indoor_inventory):
                        inventory_item = indoor_inventory[indoor_idx]
                        indoor_idx += 1
                    else:
                        continue

                    vendor_part = inventory_item.get("part_no", "")
                    serial_no = inventory_item.get("serial_no", "")

                # Handle ANTENNA items - Only process the first one
                elif "ANTENNA" in item_desc_upper:
                    if antenna_processed:
                        continue  # Skip if we've already processed one antenna item

                    antenna_processed = True  # Mark as processed
                    vendor_part = "XXXXXXXX"
                    serial_no = "XXXXXXXX"
                    item.quantity = "1"

                else:
                    vendor_part = "----------- "
                    serial_no = "--------------"

                # Item Name = item_details + service type
                item_desc = item.item_details or item.item_name
                item_name_with_type = f"{item_desc} ({get_service_type_name(item.service_type)})" if item.service_type else item_desc

                writer.writerow([
                    site_display,
                    item_name_with_type,  # Item Name column
                    item_desc,  # Item Description
                    # lvl3.sequence or
                     " ",  # Sequence from parent lvl3
                    "MW links (HW,SW,Services,Passive)",
                    vendor_part,
                    get_service_type_name(item.service_type),
                    "MW",
                    item.uom or "1",
                    item.upl_line or "NA",  # UPL Line from ItemsForLvl3
                    "1",
                    item.price or "------------",
                    serial_no,
                    inventory_item.get("software_no", "") if inventory_item else "------------",

                ])
    if site_type == "B":
        # Fetch site name
        site_name = ""
        try:
            site = db.query(Site).filter(Site.site_id == site_ip).first()
            if site:
                site_name = site.site_name
        except Exception:
            pass
        site_display = f"{site_ip} - {site_name}" if site_name else site_ip

        # Helper to map service types
        def get_service_type_name(service_types):
            if not service_types: return ""
            type_mapping = {"1": "Software", "2": "Hardware", "3": "Service"}
            return ", ".join([type_mapping.get(str(st).strip(), str(st).strip()) for st in service_types])

        outdoor_idx = 0
        indoor_idx = 0
        antenna_processed = False  # ✅ Add flag to track if antenna item has been processed
        for lvl3 in lvl3_rows:

            for item in lvl3.items:
                item_desc_upper = (item.item_details or item.item_name or "").upper()
                inventory_item = {}

                if ("OUTDOOR" in item_desc_upper) or ("INDOOR" in item_desc_upper) or ("ANTENNA" in item_desc_upper):
                    if "OUTDOOR" in item_desc_upper:
                        if outdoor_idx < len(outdoor_inventory):
                            inventory_item = outdoor_inventory[outdoor_idx]
                            outdoor_idx += 1
                        else:
                            continue  # Skip if no inventory left

                        vendor_part = inventory_item.get("part_no", "")
                        serial_no = inventory_item.get("serial_no", "")

                    # Handle INDOOR items
                    elif "INDOOR" in item_desc_upper:
                        if indoor_idx < len(indoor_inventory):
                            inventory_item = indoor_inventory[indoor_idx]
                            indoor_idx += 1
                        else:
                            continue

                        vendor_part = inventory_item.get("part_no", "")
                        serial_no = inventory_item.get("serial_no", "")

                    # Handle ANTENNA items -  Only process the first one
                    elif "ANTENNA" in item_desc_upper:
                        if antenna_processed:
                            continue  # Skip if we've already processed one antenna item

                        antenna_processed = True  # Mark as processed
                        vendor_part = "XXXXXXXX"
                        serial_no = "XXXXXXXX"
                        item.quantity = "1"

                    else:
                        vendor_part = "----------- "
                        serial_no = "--------------"

                    # Item Name = item_details + service type
                    item_desc = item.item_details or item.item_name
                    item_name_with_type = f"{item_desc} ({get_service_type_name(item.service_type)})" if item.service_type else item_desc

                    writer.writerow([
                        site_display,
                        item_name_with_type,  # Item Name column
                        item_desc,  # Item Description
                                            # lvl3.sequence or
                        " ",  # Sequence from parent lvl3
                        "MW links (HW,SW,Services,Passive)",
                        vendor_part,
                        get_service_type_name(item.service_type),
                        "MW",
                        item.uom or "1",
                        item.upl_line or "NA",  # UPL Line from ItemsForLvl3
                        "1",
                        item.price or "------------",
                        serial_no,
                        inventory_item.get("software_no", "") if inventory_item else "------------",

                    ])
    csv_string = output.getvalue()
    output.close()
    return csv_string


@BOQRouter.post("/generate-boq", response_model=None)
def generate_boq(
        payload: Dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    site_a_ip = payload.get("siteA")
    site_b_ip = payload.get("siteB")
    linked_ip = payload.get("linkedIp") or payload.get("linkid") or payload.get("labelText")
    if not linked_ip:
        raise HTTPException(status_code=400, detail="linked_ip is required in request body")

    # 1. Authorization Check
    ref = db.query(BOQReference).filter(BOQReference.linkid == linked_ip).first()
    if not ref:
        raise HTTPException(status_code=404, detail=f"No BOQ Reference found for linked_ip '{linked_ip}'.")

    project = db.query(Project).filter(Project.pid_po == ref.pid_po).first()
    if not check_project_access(current_user, project, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to generate a BOQ for this project."
        )

    # 2. Fetch all data and generate CSVs
    lvl3_rows, outdoor_inv_a, indoor_inv_a, outdoor_inv_b, indoor_inv_b, lld_row = process_boq_data(
        site_a_ip, site_b_ip, linked_ip, db
    )

    if not lld_row:
        raise HTTPException(status_code=404, detail=f"LLD data not found for linked_ip '{linked_ip}'.")
    
    csv_site_a = _generate_site_csv_content(site_a_ip, lvl3_rows, outdoor_inv_a, indoor_inv_a, db, lld_row, "A",
                                            linked_ip)
    csv_site_b = _generate_site_csv_content(site_b_ip, lvl3_rows, outdoor_inv_b, indoor_inv_b, db, lld_row, "B")

    combined_csv = csv_site_a + csv_site_b

    # Get site ID from site_a_ip for filename
    site_id = site_a_ip.replace(".", "_")

    # Return JSON response with CSV content for editing
    return {
        "status": "success",
        "message": "BOQ data generated successfully.",
        "csv_content": combined_csv,
        "site_a_total_matches": len(outdoor_inv_a) + len(indoor_inv_a),
        "site_b_total_matches": len(outdoor_inv_b) + len(indoor_inv_b)
    }


@BOQRouter.post("/download-zip")
def download_boq_zip(
        payload: Dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Download BOQ as ZIP file containing CSV and PAC Word document.

    Expected payload:
    - csv_content: The CSV content (potentially edited by user)
    - siteA: Site A IP address
    - linkedIp: Linked IP identifier
    """
    try:
        print("[DEBUG] download_boq_zip endpoint called")
        print(f"[DEBUG] Payload keys: {payload.keys()}")

        csv_content = payload.get("csv_content")
        site_a_ip = payload.get("siteA")
        linked_ip = payload.get("linkedIp") or payload.get("linkid")

        print(f"[DEBUG] csv_content length: {len(csv_content) if csv_content else 0}")
        print(f"[DEBUG] site_a_ip: {site_a_ip}")
        print(f"[DEBUG] linked_ip: {linked_ip}")

        if not csv_content:
            raise HTTPException(status_code=400, detail="csv_content is required")
        if not linked_ip:
            raise HTTPException(status_code=400, detail="linkedIp is required")
        if not site_a_ip:
            raise HTTPException(status_code=400, detail="siteA is required")

        # 1. Get project info from BOQReference
        print(f"[DEBUG] Querying BOQReference for linkid: {linked_ip}")
        ref = db.query(BOQReference).filter(BOQReference.linkid == linked_ip).first()
        if not ref:
            raise HTTPException(status_code=404, detail=f"No BOQ Reference found for linked_ip '{linked_ip}'.")
        print(f"[DEBUG] Found ref with pid_po: {ref.pid_po}")

        print(f"[DEBUG] Querying Project for pid_po: {ref.pid_po}")
        project = db.query(Project).filter(Project.pid_po == ref.pid_po).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")
        print(f"[DEBUG] Found project: {project.project_name}")

        # 2. Check access
        print("[DEBUG] Checking project access")
        if not check_project_access(current_user, project, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to download BOQ for this project."
            )
        print("[DEBUG] Access check passed")

        # 3. Extract site_id from both Site A and Site B
        site_a_formatted = site_a_ip.replace(".", "_")

        # Get Site B IP from the reference
        site_b_ip = ref.site_ip_b
        if site_b_ip:
            site_b_formatted = site_b_ip.replace(".", "_")
            site_id = f"{site_a_formatted}-{site_b_formatted}"
        else:
            site_id = site_a_formatted

        print(f"[DEBUG] site_a_ip: {site_a_ip}")
        print(f"[DEBUG] site_b_ip: {site_b_ip}")
        print(f"[DEBUG] combined site_id: {site_id}")

        # 4. Extract model name from "Implementation services" row
        print("[DEBUG] Extracting model name from CSV")
        model_name = "Implementation services - New Site"  # Default fallback

        try:
            import csv
            from io import StringIO

            csv_reader = csv.DictReader(StringIO(csv_content))
            row_count = 0

            # Print headers for debugging
            if csv_reader.fieldnames:
                print(f"[DEBUG] CSV Headers: {csv_reader.fieldnames}")

            for row in csv_reader:
                row_count += 1
                # Look for row with "Implementation services" in Model Name column
                model_col = row.get('Model Name', '').strip()

                if row_count <= 3:  # Debug first few rows
                    print(f"[DEBUG] Row {row_count} - Model Name: '{model_col}'")

                if 'Implementation services' in model_col:
                    model_name = model_col
                    print(f"[DEBUG] Found Implementation services row:")
                    print(f"[DEBUG]   Model Name: {model_name}")
                    break

            print(f"[DEBUG] Processed {row_count} rows")
            print(f"[DEBUG] Final Model Name: {model_name}")
        except Exception as e:
            print(f"[DEBUG] Error extracting model name from CSV: {str(e)}")
            import traceback
            traceback.print_exc()

        # 5. Get template path
        template_path = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "PAC_Template.docx")
        print(f"[DEBUG] template_path: {template_path}")
        print(f"[DEBUG] Template exists: {os.path.exists(template_path)}")

        # 6. Generate ZIP package
        print("[DEBUG] Calling create_boq_zip_package")
        zip_buffer = create_boq_zip_package(
            csv_content=csv_content,
            site_id=site_id,
            project_name=project.project_name,
            project_po=project.pid_po,
            link_id=linked_ip,  # Pass link ID for certificate number
            template_path=template_path,
            csv_filename=f"BOQ_{site_id}.csv",
            model_name=model_name
        )
        print(f"[DEBUG] ZIP buffer size: {zip_buffer.tell()}")

        # 6. Return ZIP file as download
        print("[DEBUG] Returning StreamingResponse")
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=BOQ_{site_id}.zip"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error in download_boq_zip: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate ZIP package: {str(e)}")


@BOQRouter.delete("/delete-all-references/{project_id}")
def delete_all_references_for_project(
        project_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes all BOQ references for a project.
    Users need 'all' permission on the project to delete all references.

    Returns:
    - deleted_references: Number of BOQ references deleted
    - affected_tables: List of tables that had data deleted
    """
    # Check if project exists and user has access
    project = get_project_for_boq(project_id, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check user has 'all' permission
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete BOQ references for this project. Contact the Senior Admin."
        )

    try:
        # Get count of references for this project
        references_count = db.query(BOQReference).filter(BOQReference.pid_po == project_id).count()

        if references_count == 0:
            raise HTTPException(status_code=404, detail="No BOQ references found for this project")

        # Delete all BOQ references for this project
        references_deleted = db.query(BOQReference).filter(BOQReference.pid_po == project_id).delete(synchronize_session=False)

        db.commit()

        return {
            "message": "All BOQ references deleted successfully",
            "deleted_references": references_deleted,
            "affected_tables": ["boq_references"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete BOQ references: {str(e)}")
