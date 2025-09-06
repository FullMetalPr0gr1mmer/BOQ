import csv
from io import StringIO
from typing import Dict, Any, List
from typing import Optional
from fastapi import APIRouter, UploadFile, File, status
from fastapi import Body, HTTPException
from fastapi import Query, Depends
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from APIs.Core import get_db, _parse_interface_name, _sa_row_to_dict
from Models.BOQReference import BOQReference
from Models.Inventory import Inventory
from Schemas.BOQReferenceSchema import BOQReferenceOut
from Models.LLD import LLD
from Models.Levels import Lvl3
from Models.Inventory import Inventory
from Models.BOQReference import BOQReference
from Models.Site import Site
from Models.Dismantling import Dismantling  # Assuming table exists
from fastapi import HTTPException, Depends, Body, APIRouter
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

import csv
from io import StringIO
from typing import Dict, Any, List, Tuple
import datetime
import os
from sqlalchemy import and_
#
BOQRouter = APIRouter(prefix="/boq", tags=["BOQ Generation"])
EXPECTED_HEADERS = ["linkid", "InterfaceName", "SiteIPA", "SiteIPB"]

@BOQRouter.post("/upload-reference", response_model=Dict[str, int], status_code=status.HTTP_201_CREATED)
async def upload_reference_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="ignore")
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty file")

        # detect delimiter (tab fallback)
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(text)
        except Exception:
            class _Tsv(csv.Dialect):
                delimiter = "\t"; quotechar = '"'; escapechar = None
                doublequote = True; skipinitialspace = False
                lineterminator = "\n"; quoting = csv.QUOTE_MINIMAL
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
            interface_name = (row.get("InterfaceName") or "").strip()
            site_ip_a = (row.get("SiteIPA") or "").strip()
            site_ip_b = (row.get("SiteIPB") or "").strip()
            if not any([linkid, interface_name, site_ip_a, site_ip_b]):
                continue
            to_insert.append(BOQReference(
                linkid=linkid,
                interface_name=interface_name or None,
                site_ip_a=site_ip_a or None,
                site_ip_b=site_ip_b or None,
            ))

        if not to_insert:
            raise HTTPException(status_code=400, detail="No valid rows found")

        db.bulk_save_objects(to_insert)
        db.commit()
        return {"rows_processed": processed, "rows_inserted": len(to_insert)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {e}")

@BOQRouter.get("/reference/{id}", response_model=BOQReferenceOut)
def get_reference(id: str, db: Session = Depends(get_db)):
    # Query by string ID
    row = db.query(BOQReference).filter(BOQReference.id == id).first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Reference with id '{id}' not found")

    # Convert SQLAlchemy model to Pydantic schema for proper serialization
    return BOQReferenceOut.model_validate(row).model_dump(by_alias=True)

#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////


@BOQRouter.get("/references")
def list_references(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Filter by linkid/interface/site IP (case-insensitive)"),
    db: Session = Depends(get_db)
):
    q = db.query(BOQReference)

    if search:
        s = f"%{search.strip().lower()}%"
        # coalesce -> safe when columns are NULL
        q = q.filter(or_(
            func.lower(func.coalesce(BOQReference.linkid, "")).like(s),
            func.lower(func.coalesce(BOQReference.interface_name, "")).like(s),
            func.lower(func.coalesce(BOQReference.site_ip_a, "")).like(s),
            func.lower(func.coalesce(BOQReference.site_ip_b, "")).like(s),
        ))

    total = q.count()
    rows = (
        q.order_by(BOQReference.created_at.desc())
         .offset(skip)
         .limit(limit)
         .all()
    )

    return {
        "total": total,
        "items": [BOQReferenceOut.model_validate(r).model_dump(by_alias=True) for r in rows]
    }



# from main import BOQRouter, get_db  # make sure you have these
# from utils.db import get_db

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

    return lvl3_rows, outdoor_inventory_a, indoor_inventory_a, outdoor_inventory_b, indoor_inventory_b, lld_row


def _generate_site_csv_content(site_ip: str, lvl3_rows: List, outdoor_inventory: List[Dict],
                               indoor_inventory: List[Dict], db: Session, lld_row: LLD, site_type: str) -> str:
    """Generate CSV content for a site with repeated OUTDOOR/INDOOR items and antenna handling."""

    output = StringIO()
    writer = csv.writer(output)

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

    # CSV Headers
    headers = ["Site_IP", "Item Description", "L1 Category", "Vendor Part Number", "Type", "Category", "UOM",
               "Total Qtts", "Discounted unit price", "SN", "SW Number"]
    writer.writerow(headers)

    outdoor_idx = 0
    indoor_idx = 0
    antenna_processed = False  # ✅ Add flag to track if antenna item has been processed

    for lvl3 in lvl3_rows:

        # Parent row
        writer.writerow([
            site_display,
            lvl3.item_name,
            "MW links (HW,SW,Services,Passive)",
            "-----------------",  # Vendor Part Number
            get_service_type_name(lvl3.service_type),
            "MW",
            "Link",
            lvl3.total_quantity or "",
            lvl3.total_price or "",
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

            # Handle ANTENNA items - ✅ Only process the first one
            elif "ANTENNA" in item_desc_upper:
                if antenna_processed:
                    continue  # Skip if we've already processed one antenna item

                antenna_processed = True  # Mark as processed
                vendor_part = "XXXXXXXX"
                serial_no = "XXXXXXXX"

                # Fill NE/FE sizes
                if site_type == "A":
                    item.quantity = getattr(lld_row, "ne_ant_size", "")
                elif site_type == "B":
                    item.quantity = getattr(lld_row, "fe_ant_size", "")
                if not item.quantity:
                    item.quantity = "XXXXXXXX"

            else:
                vendor_part = "----------- "
                serial_no = "--------------"

            writer.writerow([
                site_display,
                item.item_details or item.item_name,
                "MW links (HW,SW,Services,Passive)",
                vendor_part,
                get_service_type_name(item.service_type),
                "MW",
                item.uom or "1",
                item.quantity or "----------",
                item.price or "------------",
                serial_no,
                inventory_item.get("software_no", "") if inventory_item else "------------",

            ])

    csv_string = output.getvalue()
    output.close()
    return csv_string


@BOQRouter.post("/generate-boq")
def generate_boq(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> Dict[str, Any]:
    site_a_ip = payload.get("siteA")
    site_b_ip = payload.get("siteB")
    linked_ip = payload.get("linkedIp") or payload.get("linkid") or payload.get("labelText")
    if not linked_ip:
        raise HTTPException(status_code=400, detail="linked_ip is required in request body")

    # Fetch all data
    lvl3_rows, outdoor_inv_a, indoor_inv_a, outdoor_inv_b, indoor_inv_b, lld_row = process_boq_data(
        site_a_ip, site_b_ip, linked_ip, db
    )

    # Generate CSVs
    csv_site_a = _generate_site_csv_content(site_a_ip, lvl3_rows, outdoor_inv_a, indoor_inv_a, db, lld_row, "A")
    csv_site_b = _generate_site_csv_content(site_b_ip, lvl3_rows, outdoor_inv_b, indoor_inv_b, db, lld_row, "B")

    # Combine CSVs
    combined_csv = csv_site_a + "\n" + csv_site_b
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"BOQ_SiteA-{site_a_ip}_SiteB-{site_b_ip}_{linked_ip}_{timestamp}.csv"
    filepath = f"./downloads/{filename}"

    os.makedirs("./downloads", exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        f.write(combined_csv)

    return {
        "status": "success",
        "message": "BOQ data generated successfully.",
        "csv_content": combined_csv,  # ✅ Return the CSV content directly
        "site_a_total_matches": len(outdoor_inv_a) + len(indoor_inv_a),
        "site_b_total_matches": len(outdoor_inv_b) + len(indoor_inv_b)
    }
