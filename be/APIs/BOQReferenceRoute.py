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

from Models.LLD import LLD
from Models.Levels import Lvl3
# @BOQRouter.post("/generate-boq")
# def generate_boq(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> Dict[str, Any]:
#
#     site_a_ip = payload.get("siteA")
#     site_b_ip = payload.get("siteB")
#     linked_ip = payload.get("linkedIp") or payload.get("linkid") or payload.get("labelText")
#     if not linked_ip:
#         raise HTTPException(status_code=400, detail="linked_ip is required in request body")
#
#     # 1️⃣ Fetch matching BOQReference rows
#     refs: List[BOQReference] = db.query(BOQReference).filter(
#         BOQReference.site_ip_a == site_a_ip,
#         BOQReference.site_ip_b == site_b_ip
#     ).all()
#
#     results = []
#     for ref in refs:
#         parsed = _parse_interface_name(ref.interface_name)
#
#         # Inventory search Site-A
#         inv_a_matches = []
#         if ref.site_ip_a and parsed["a_slot"] is not None and parsed["a_port"] is not None:
#             inv_rows_a = (
#                 db.query(Inventory)
#                 .filter(
#                     Inventory.site_id == ref.site_ip_a,
#                     Inventory.slot_id == parsed["a_slot"],
#                     Inventory.port_id == parsed["a_port"],
#                 )
#                 .all()
#             )
#             inv_a_matches = [_sa_row_to_dict(r) for r in inv_rows_a]
#
#         # Inventory search Site-B
#         inv_b_matches = []
#         if ref.site_ip_b and parsed["b_slot"] is not None and parsed["b_port"] is not None:
#             inv_rows_b = (
#                 db.query(Inventory)
#                 .filter(
#                     Inventory.site_id == ref.site_ip_b,
#                     Inventory.slot_id == parsed["b_slot"],
#                     Inventory.port_id == parsed["b_port"],
#                 )
#                 .all()
#             )
#             inv_b_matches = [_sa_row_to_dict(r) for r in inv_rows_b]
#
#         results.append({
#             "reference": BOQReferenceOut.model_validate(ref).model_dump(by_alias=True),
#             "parsed_interface": parsed,
#             "inventory_site_a_matches": inv_a_matches,
#             "inventory_site_b_matches": inv_b_matches,
#         })
#
#     lld_row = db.query(LLD).filter(LLD.link_id == linked_ip).first()
#     print("---- LLD Row ----")
#     if lld_row:
#         print(f"Linked IP: {lld_row.link_id}")
#         print(f"Item Name / Config: {lld_row.item_name}")
#     else:
#         print("No LLD row found for this linked IP")
#
#     lvl3_rows = []
#     if lld_row and lld_row.item_name:
#         lvl3_rows = db.query(Lvl3).filter(Lvl3.item_name == lld_row.item_name).all()
#
#     for lvl3 in lvl3_rows:
#         print("---- Lvl3 ----")
#         print(f"ID: {lvl3.id}, Project: {lvl3.project_name}, Item Name: {lvl3.item_name}, UOM: {lvl3.uom}, Total Qty: {lvl3.total_quantity}, Total Price: {lvl3.total_price}, Service Type: {lvl3.service_type}")
#         print("---- ItemsForLvl3 ----")
#         for item in lvl3.items:
#             print(f"ID: {item.id}, Name: {item.item_name}, Details: {item.item_details}, Vendor PN: {item.vendor_part_number}, Category: {item.category}, UOM: {item.uom}, Qty: {item.quantity}, Price: {item.price}, Service Type: {item.service_type}")
#
#     # Append LLD and Lvl3 info to final results
#     return {
#         "linked_ip": linked_ip,
#         "matches": results,
#         "lld_row": {
#             "link_id": lld_row.link_id if lld_row else None,
#             "item_name": lld_row.item_name if lld_row else None
#         },
#         "lvl3_matches": [lvl3.id for lvl3 in lvl3_rows]
#     }

import csv
from io import StringIO
from typing import Dict, Any, List
from fastapi import HTTPException, Depends, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import datetime


@BOQRouter.post("/generate-boq-download")
def generate_boq_download(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> StreamingResponse:
    site_a_ip = payload.get("siteA")
    site_b_ip = payload.get("siteB")
    linked_ip = payload.get("linkedIp") or payload.get("linkid") or payload.get("labelText")
    if not linked_ip:
        raise HTTPException(status_code=400, detail="linked_ip is required in request body")

    # 1️⃣ Fetch matching BOQReference rows
    refs: List[BOQReference] = db.query(BOQReference).filter(
        BOQReference.site_ip_a == site_a_ip,
        BOQReference.site_ip_b == site_b_ip
    ).all()

    results = []
    for ref in refs:
        parsed = _parse_interface_name(ref.interface_name)

        # Inventory search Site-A
        inv_a_matches = []
        if ref.site_ip_a and parsed["a_slot"] is not None and parsed["a_port"] is not None:
            inv_rows_a = (
                db.query(Inventory)
                .filter(
                    Inventory.site_id == ref.site_ip_a,
                    Inventory.slot_id == parsed["a_slot"],
                    Inventory.port_id == parsed["a_port"],
                )
                .all()
            )
            inv_a_matches = [_sa_row_to_dict(r) for r in inv_rows_a]

        # Inventory search Site-B
        inv_b_matches = []
        if ref.site_ip_b and parsed["b_slot"] is not None and parsed["b_port"] is not None:
            inv_rows_b = (
                db.query(Inventory)
                .filter(
                    Inventory.site_id == ref.site_ip_b,
                    Inventory.slot_id == parsed["b_slot"],
                    Inventory.port_id == parsed["b_port"],
                )
                .all()
            )
            inv_b_matches = [_sa_row_to_dict(r) for r in inv_rows_b]

        results.append({
            "reference": BOQReferenceOut.model_validate(ref).model_dump(by_alias=True),
            "parsed_interface": parsed,
            "inventory_site_a_matches": inv_a_matches,
            "inventory_site_b_matches": inv_b_matches,
        })

    lld_row = db.query(LLD).filter(LLD.link_id == linked_ip).first()
    print("---- LLD Row ----")
    if lld_row:
        print(f"Linked IP: {lld_row.link_id}")
        print(f"Item Name / Config: {lld_row.item_name}")
    else:
        print("No LLD row found for this linked IP")

    lvl3_rows = []
    if lld_row and lld_row.item_name:
        lvl3_rows = db.query(Lvl3).filter(Lvl3.item_name == lld_row.item_name).all()

    for lvl3 in lvl3_rows:
        print("---- Lvl3 ----")
        print(
            f"ID: {lvl3.id}, Project: {lvl3.project_name}, Item Name: {lvl3.item_name}, UOM: {lvl3.uom}, Total Qty: {lvl3.total_quantity}, Total Price: {lvl3.total_price}, Service Type: {lvl3.service_type}")
        print("---- ItemsForLvl3 ----")
        for item in lvl3.items:
            print(
                f"ID: {item.id}, Name: {item.item_name}, Details: {item.item_details}, Vendor PN: {item.vendor_part_number}, Category: {item.category}, UOM: {item.uom}, Qty: {item.quantity}, Price: {item.price}, Service Type: {item.service_type}")

    # Generate and return CSV as downloadable file
    csv_content = generate_csv_content(site_a_ip, results, lvl3_rows)

    # Create filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"BOQ_{site_a_ip}_{linked_ip}_{timestamp}.csv"

    # Convert string to bytes for streaming
    csv_bytes = csv_content.encode('utf-8')

    # Return CSV as immediate download
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


def generate_csv_content(site_a_ip: str, results: List[Dict], lvl3_rows: List, db: Session) -> str:
    """
    Generate CSV content based on Site A IP, inventory matches, and Lvl3 data
    """
    output = StringIO()
    writer = csv.writer(output)

    # Get site name from database
    site_name = ""
    try:
        from your_models import Sites  # Adjust import as needed
        site = db.query(Sites).filter(Sites.site_id == site_a_ip).first()
        if site:
            site_name = site.site_name
    except:
        pass  # If site lookup fails, just use IP

    # Format site info: "IP - Site Name" or just IP if no name found
    site_display = f"{site_a_ip} - {site_name}" if site_name else site_a_ip

    # Service type mapping function
    def get_service_type_name(service_types):
        """Convert service type numbers/codes to names"""
        if not service_types:
            return ""

        type_mapping = {
            "1": "Software",
            "2": "Hardware",
            "3": "Service",
            "Software": "Software",
            "Hardware": "Hardware",
            "Service": "Service"
        }

        names = []
        for service_type in service_types:
            service_type_str = str(service_type).strip()
            mapped_name = type_mapping.get(service_type_str, service_type_str)
            names.append(mapped_name)

        return ", ".join(names)

    # CSV Headers
    headers = [
        "Site_IP",
        "Item Description",
        "L1 Category",
        "Vendor Part Number",
        "Type",
        "Category",
        "UOM",
        "Total Qtts",
        "Discounted unit price",
        "SN",
        "SW Number"
    ]
    writer.writerow(headers)

    # Get total inventory matches for Site A across all results
    total_site_a_matches = 0
    all_site_a_inventory = []

    for result in results:
        site_a_matches = result.get("inventory_site_a_matches", [])
        total_site_a_matches += len(site_a_matches)
        all_site_a_inventory.extend(site_a_matches)

    print(f"Total Site A inventory matches: {total_site_a_matches}")

    # Process each Lvl3 row
    for lvl3 in lvl3_rows:
        # First, add row for the Lvl3 itself (no inventory data for Lvl3)
        lvl3_row = [
            site_display,  # Site_IP with name
            lvl3.item_name,  # Item Description
            "MW links (HW,SW,Services,Passive)",  # L1 Category
            "",  # Vendor Part Number - empty for Lvl3
            get_service_type_name(lvl3.service_type),  # Type - convert to names
            "MW",  # Category
            "Link",  # UOM for Lvl3 is "Link"
            lvl3.total_quantity or "",  # Total Qtts
            lvl3.total_price or "",  # Discounted unit price
            "",  # SN - empty for Lvl3
            ""  # SW Number - empty for Lvl3
        ]
        writer.writerow(lvl3_row)

        # Then add rows for ItemsForLvl3, limited by inventory matches
        items_to_process = min(len(lvl3.items), total_site_a_matches)

        for i, item in enumerate(lvl3.items[:items_to_process]):
            # Get corresponding inventory item (if available)
            inventory_item = all_site_a_inventory[i] if i < len(all_site_a_inventory) else {}

            item_row = [
                site_display,  # Site_IP with name
                item.item_details or item.item_name,  # Item Description
                "MW links (HW,SW,Services,Passive)",  # L1 Category
                inventory_item.get("part_no", ""),  # Vendor Part Number from inventory only
                get_service_type_name(item.service_type),  # Type - convert to names
                "MW",  # Category
                item.uom or "1",  # UOM - use item's UOM or default to "1"
                item.quantity or "",  # Total Qtts
                item.price or "",  # Discounted unit price
                inventory_item.get("serial_no", ""),  # SN from inventory (only for items)
                inventory_item.get("software_no", "")  # SW Number from inventory (only for items)
            ]
            writer.writerow(item_row)

    csv_string = output.getvalue()
    output.close()

    return csv_string


def generate_csv_content_site_b(site_b_ip: str, results: List[Dict], lvl3_rows: List, db: Session) -> str:
    """
    Generate CSV content for Site B - same logic as Site A but using Site B inventory matches
    """
    output = StringIO()
    writer = csv.writer(output)

    # Get site name from database for Site B
    site_name = ""
    try:
        from your_models import Sites  # Adjust import as needed
        site = db.query(Sites).filter(Sites.site_id == site_b_ip).first()
        if site:
            site_name = site.site_name
    except:
        pass  # If site lookup fails, just use IP

    # Format site info: "IP - Site Name" or just IP if no name found
    site_display = f"{site_b_ip} - {site_name}" if site_name else site_b_ip

    # Service type mapping function
    def get_service_type_name(service_types):
        """Convert service type numbers/codes to names"""
        if not service_types:
            return ""

        type_mapping = {
            "1": "Software",
            "2": "Hardware",
            "3": "Service",
            "Software": "Software",
            "Hardware": "Hardware",
            "Service": "Service"
        }

        names = []
        for service_type in service_types:
            service_type_str = str(service_type).strip()
            mapped_name = type_mapping.get(service_type_str, service_type_str)
            names.append(mapped_name)

        return ", ".join(names)

    # CSV Headers (same as Site A)
    headers = [
        "Site_IP",
        "Item Description",
        "L1 Category",
        "Vendor Part Number",
        "Type",
        "Category",
        "UOM",
        "Total Qtts",
        "Discounted unit price",
        "SN",
        "SW Number"
    ]
    writer.writerow(headers)

    # Get total inventory matches for Site B across all results
    total_site_b_matches = 0
    all_site_b_inventory = []

    for result in results:
        site_b_matches = result.get("inventory_site_b_matches", [])
        total_site_b_matches += len(site_b_matches)
        all_site_b_inventory.extend(site_b_matches)

    print(f"Total Site B inventory matches: {total_site_b_matches}")

    # Process each Lvl3 row (same logic but with Site B data)
    for lvl3 in lvl3_rows:
        # First, add row for the Lvl3 itself (no inventory data for Lvl3)
        lvl3_row = [
            site_display,  # Site_IP with name (Site B)
            lvl3.item_name,  # Item Description
            "MW links (HW,SW,Services,Passive)",  # L1 Category
            "",  # Vendor Part Number - empty for Lvl3
            get_service_type_name(lvl3.service_type),  # Type - convert to names
            "MW",  # Category
            "Link",  # UOM for Lvl3 is "Link"
            lvl3.total_quantity or "",  # Total Qtts
            lvl3.total_price or "",  # Discounted unit price
            "",  # SN - empty for Lvl3
            ""  # SW Number - empty for Lvl3
        ]
        writer.writerow(lvl3_row)

        # Then add rows for ItemsForLvl3, limited by Site B inventory matches
        items_to_process = min(len(lvl3.items), total_site_b_matches)

        for i, item in enumerate(lvl3.items[:items_to_process]):
            # Get corresponding Site B inventory item (if available)
            inventory_item = all_site_b_inventory[i] if i < len(all_site_b_inventory) else {}

            item_row = [
                site_display,  # Site_IP with name (Site B)
                item.item_details or item.item_name,  # Item Description
                "MW links (HW,SW,Services,Passive)",  # L1 Category
                inventory_item.get("part_no", ""),  # Vendor Part Number from Site B inventory
                get_service_type_name(item.service_type),  # Type - convert to names
                "MW",  # Category
                item.uom or "1",  # UOM - use item's UOM or default to "1"
                item.quantity or "",  # Total Qtts
                item.price or "",  # Discounted unit price
                inventory_item.get("serial_no", ""),  # SN from Site B inventory
                inventory_item.get("software_no", "")  # SW Number from Site B inventory
            ]
            writer.writerow(item_row)

    csv_string = output.getvalue()
    output.close()

    return csv_string


# Main endpoint for immediate CSV download
@BOQRouter.post("/generate-boq")
def generate_boq(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Main endpoint that processes the BOQ and saves CSV locally, then returns success message
    """
    site_a_ip = payload.get("siteA")
    site_b_ip = payload.get("siteB")
    linked_ip = payload.get("linkedIp") or payload.get("linkid") or payload.get("labelText")
    if not linked_ip:
        raise HTTPException(status_code=400, detail="linked_ip is required in request body")

    # Process all the data (same logic as download endpoint)
    refs, results, lld_row, lvl3_rows = process_boq_data(site_a_ip, site_b_ip, linked_ip, db)

    # Generate CSV content for Site A
    csv_content_site_a = generate_csv_content(site_a_ip, results, lvl3_rows, db)

    # Generate CSV content for Site B
    csv_content_site_b = generate_csv_content_site_b(site_b_ip, results, lvl3_rows, db)

    # Combine both tables with a separator
    combined_csv = csv_content_site_a + "\n\n" + csv_content_site_b

    # Save combined CSV file immediately to server/local directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"BOQ_SiteA-{site_a_ip}_SiteB-{site_b_ip}_{linked_ip}_{timestamp}.csv"
    filepath = f"./downloads/{filename}"  # Adjust path as needed

    # Create downloads directory if it doesn't exist
    import os
    os.makedirs("./downloads", exist_ok=True)

    # Save combined file immediately
    with open(filepath, 'w', newline='', encoding='utf-8') as file:
        file.write(combined_csv)

    print(f"Combined CSV file saved to: {filepath}")

    # Return success response
    return {
        "status": "success",
        "message": f"BOQ CSV file with both Site A and Site B generated and saved as {filename}",
        "filepath": filepath,
        "linked_ip": linked_ip,
        "site_a_ip": site_a_ip,
        "site_b_ip": site_b_ip,
        "total_lvl3_records": len(lvl3_rows),
        "total_site_a_matches": sum(len(r.get("inventory_site_a_matches", [])) for r in results),
        "total_site_b_matches": sum(len(r.get("inventory_site_b_matches", [])) for r in results)
    }


def process_boq_data(site_a_ip: str, site_b_ip: str, linked_ip: str, db: Session):
    """
    Helper function to process all BOQ data
    """
    # Fetch matching BOQReference rows
    refs: List[BOQReference] = db.query(BOQReference).filter(
        BOQReference.site_ip_a == site_a_ip,
        BOQReference.site_ip_b == site_b_ip
    ).all()

    results = []
    for ref in refs:
        parsed = _parse_interface_name(ref.interface_name)

        # Inventory search Site-A
        inv_a_matches = []
        if ref.site_ip_a and parsed["a_slot"] is not None and parsed["a_port"] is not None:
            inv_rows_a = (
                db.query(Inventory)
                .filter(
                    Inventory.site_id == ref.site_ip_a,
                    Inventory.slot_id == parsed["a_slot"],
                    Inventory.port_id == parsed["a_port"],
                )
                .all()
            )
            inv_a_matches = [_sa_row_to_dict(r) for r in inv_rows_a]

        # Inventory search Site-B
        inv_b_matches = []
        if ref.site_ip_b and parsed["b_slot"] is not None and parsed["b_port"] is not None:
            inv_rows_b = (
                db.query(Inventory)
                .filter(
                    Inventory.site_id == ref.site_ip_b,
                    Inventory.slot_id == parsed["b_slot"],
                    Inventory.port_id == parsed["b_port"],
                )
                .all()
            )
            inv_b_matches = [_sa_row_to_dict(r) for r in inv_rows_b]

        results.append({
            "reference": BOQReferenceOut.model_validate(ref).model_dump(by_alias=True),
            "parsed_interface": parsed,
            "inventory_site_a_matches": inv_a_matches,
            "inventory_site_b_matches": inv_b_matches,
        })

    lld_row = db.query(LLD).filter(LLD.link_id == linked_ip).first()
    print("---- LLD Row ----")
    if lld_row:
        print(f"Linked IP: {lld_row.link_id}")
        print(f"Item Name / Config: {lld_row.item_name}")
    else:
        print("No LLD row found for this linked IP")

    lvl3_rows = []
    if lld_row and lld_row.item_name:
        lvl3_rows = db.query(Lvl3).filter(Lvl3.item_name == lld_row.item_name).all()

    for lvl3 in lvl3_rows:
        print("---- Lvl3 ----")
        print(
            f"ID: {lvl3.id}, Project: {lvl3.project_name}, Item Name: {lvl3.item_name}, UOM: {lvl3.uom}, Total Qty: {lvl3.total_quantity}, Total Price: {lvl3.total_price}, Service Type: {lvl3.service_type}")
        print("---- ItemsForLvl3 ----")
        for item in lvl3.items:
            print(
                f"ID: {item.id}, Name: {item.item_name}, Details: {item.item_details}, Vendor PN: {item.vendor_part_number}, Category: {item.category}, UOM: {item.uom}, Qty: {item.quantity}, Price: {item.price}, Service Type: {item.service_type}")

    return refs, results, lld_row, lvl3_rows
