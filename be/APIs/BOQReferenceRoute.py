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

@BOQRouter.post("/generate-boq")
def generate_boq(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> Dict[str, Any]:

    #payload example: { "linked_ip": "JIZ0243-JIZ0169" }
    site_a_ip = payload.get("siteA")
    site_b_ip = payload.get("siteB")


    """ Steps:
    - find BOQReference rows where linkid == linked_ip
    - parse interface_name into slot/port for A and B
    - search Inventory where site_id == site_ip AND slot_id == parsed_slot AND port_id == parsed_port
    - return the findings for inspection (no DB writes yet)
    """

    linked_ip = payload.get("linkedIp") or payload.get("linkid") or payload.get("labelText")
    if not linked_ip:
        raise HTTPException(status_code=400, detail="linked_ip is required in request body")

    # fetch matching BOQ references
    refs: List[BOQReference] = db.query(BOQReference).filter(
        BOQReference.site_ip_a == site_a_ip and BOQReference.site_ip_b == site_b_ip).all()

    results = []
    for ref in refs:
        parsed = _parse_interface_name(ref.interface_name)

        # Inventory search for Site-A
        inv_a_matches = []
        if ref.site_ip_a and parsed["a_slot"] is not None and parsed["a_port"] is not None:
            # adjust Inventory.site_id / slot_id / port_id names if your model differs
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

        # Inventory search for Site-B
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

    return {"linked_ip": linked_ip, "matches": results}


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
# @BOQRouter.post("/generate-boq")
# def generate_boq(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> Dict[str, Any]:
#     """
#     payload example: {
#       "linkedIp": "JIZ0243-JIZ0169",
#       "interfaceName": "1-1-1-10",
#       "siteA": "SiteIPA",
#       "siteB": "SiteIPB"
#     }
#     Steps:
#       - parse interface_name into slot/port for A and B
#       - search Inventory where site_id == site_ip AND slot_id == parsed_slot AND port_id == parsed_port
#       - return the findings (no DB writes yet)
#     """
#     print("/////////////////////////////////////////////////////////////////////////")
#     print(payload)
#     print("/////////////////////////////////////////////////////////////////////////")
#
#     linked_ip = payload.get("linkedIp")
#     interface_name = payload.get("interfaceName")
#     site_a_ip = payload.get("siteA")
#     site_b_ip = payload.get("siteB")
#
#     if not linked_ip or not interface_name:
#         raise HTTPException(status_code=400, detail="linkedIp and interfaceName are required")
#
#     parsed = _parse_interface_name(interface_name)
#
#     # Inventory search for Site-A
#     inv_a_matches = []
#     if site_a_ip and parsed["a_slot"] is not None and parsed["a_port"] is not None:
#         inv_rows_a = (
#             db.query(Inventory)
#             .filter(
#                 Inventory.site_id == site_a_ip,
#                 Inventory.slot_id == parsed["a_slot"],
#                 Inventory.port_id == parsed["a_port"],
#             )
#             .all()
#         )
#         inv_a_matches = [_sa_row_to_dict(r) for r in inv_rows_a]
#
#     # Inventory search for Site-B
#     inv_b_matches = []
#     if site_b_ip and parsed["b_slot"] is not None and parsed["b_port"] is not None:
#         inv_rows_b = (
#             db.query(Inventory)
#             .filter(
#                 Inventory.site_id == site_b_ip,
#                 Inventory.slot_id == parsed["b_slot"],
#                 Inventory.port_id == parsed["b_port"],
#             )
#             .all()
#         )
#         inv_b_matches = [_sa_row_to_dict(r) for r in inv_rows_b]
#
#     return {
#         "linked_ip": linked_ip,
#         "matches": [
#             {
#                 "reference": payload,   # we just echo the row instead of fetching BOQReference
#                 "parsed_interface": parsed,
#                 "inventory_site_a_matches": inv_a_matches,
#                 "inventory_site_b_matches": inv_b_matches,
#             }
#         ]
#     }
