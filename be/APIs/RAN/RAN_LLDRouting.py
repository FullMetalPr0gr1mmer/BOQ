import csv
from io import StringIO
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

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
        )
        db.add(site)
        i=i+1
    db.commit()
    return {"inserted":i}
