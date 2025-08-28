from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
from io import StringIO

from APIs.Core import get_db
from Models.LLD import LLD
from Schemas.LLDSchema import LLDCreate, LLDOut
from pydantic import BaseModel

lld_router = APIRouter(prefix="/lld", tags=["LLD"])

# Wrapper schema for GET response
class LLDListOut(BaseModel):
    total: int
    items: List[LLDOut]

    class Config:
        orm_mode = True

# ---------------- GET (list with pagination + search) ----------------
@lld_router.get("", response_model=LLDListOut)
def get_lld(
    skip: int = 0,
    limit: int = 100,
    link_id: str = "",
    db: Session = Depends(get_db)
):
    query = db.query(LLD)
    if link_id:
        query = query.filter(LLD.link_id.contains(link_id))
    total = query.count()
    # MSSQL requires order_by when using offset/limit
    items = query.order_by(LLD.id).offset(skip).limit(limit).all()
    return {"total": total, "items": items}

# ---------------- POST (create single row) ----------------
@lld_router.post("", response_model=LLDOut)
def create_lld(data: LLDCreate, db: Session = Depends(get_db)):
    db_obj = LLD(**data.dict())
    db.add(db_obj)
    try:
        db.commit()
        db.refresh(db_obj)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return db_obj

# ---------------- PUT (update row) ----------------
@lld_router.put("/{link_id}", response_model=LLDOut)
def update_lld(link_id: str, data: LLDCreate, db: Session = Depends(get_db)):
    db_obj = db.query(LLD).filter(LLD.link_id == link_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="LLD row not found")
    for key, value in data.dict().items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# ---------------- DELETE ----------------
@lld_router.delete("/{link_id}")
def delete_lld(link_id: str, db: Session = Depends(get_db)):
    db_obj = db.query(LLD).filter(LLD.link_id == link_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="LLD row not found")
    db.delete(db_obj)
    db.commit()
    return {"detail": f"{link_id} deleted successfully"}

# ---------------- CSV Upload ----------------
@lld_router.post("/upload-csv")
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type")
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    inserted = 0
    for row in reader:
        try:
            lld_row = LLD(
                link_id=row.get("link ID","").strip(),
                action=row.get("Action","").strip(),
                fon=row.get("FON","").strip(),
                item_name=row.get("configuration","").strip(),
                distance=row.get("Distance","").strip(),
                scope=row.get("Scope","").strip(),
                ne=row.get("NE","").strip(),
                fe=row.get("FE","").strip(),
                link_category=row.get("link catergory","").strip(),
                link_status=row.get("Link status","").strip(),
                comments=row.get("COMMENTS","").strip(),
                dismanting_link_id=row.get("Dismanting link ID","").strip(),
                band=row.get("Band","").strip(),
                t_band_cs=row.get("T-band CS","").strip(),
                ne_ant_size=row.get("NE Ant size","").strip(),
                fe_ant_size=row.get("FE Ant Size","").strip(),
                sd_ne=row.get("SD NE","").strip(),
                sd_fe=row.get("SD FE","").strip(),
                odu_type=row.get("ODU TYPE","").strip(),
                updated_sb=row.get("Updated SB","").strip(),
                region=row.get("Region","").strip(),
                losr_approval=row.get("LOSR approval","").strip(),
                initial_lb=row.get("initial LB","").strip(),
                flb=row.get("FLB","").strip(),
            )
            db.add(lld_row)
            inserted += 1
        except Exception:
            db.rollback()
            continue
    db.commit()
    return {"rows_inserted": inserted}
