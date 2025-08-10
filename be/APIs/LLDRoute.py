from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from APIs.Core import get_db
from Models.LLD import LLD
from Schemas.LLDSchema import LLDCreate, LLDOut


router = APIRouter(prefix="/lld", tags=["LLD"])


# Create LLD
@router.post("/create", response_model=LLDOut)
def create_lld(lld: LLDCreate, db: Session = Depends(get_db)):
    existing = db.query(LLD).filter(LLD.link_id == lld.link_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="LLD with this link_id already exists.")

    new_lld = LLD(**lld.dict())
    db.add(new_lld)
    db.commit()
    db.refresh(new_lld)
    return new_lld


# Get all LLDs
@router.get("/", response_model=List[LLDOut])
def get_all_llds(db: Session = Depends(get_db)):
    return db.query(LLD).all()


# Get LLD by link_id
@router.get("/{link_id}", response_model=LLDOut)
def get_lld(link_id: str, db: Session = Depends(get_db)):
    lld = db.query(LLD).filter(LLD.link_id == link_id).first()
    if not lld:
        raise HTTPException(status_code=404, detail="LLD not found.")
    return lld


# Update LLD
@router.put("/{link_id}", response_model=LLDOut)
def update_lld(link_id: str, updated: LLDCreate, db: Session = Depends(get_db)):
    lld = db.query(LLD).filter(LLD.link_id == link_id).first()
    if not lld:
        raise HTTPException(status_code=404, detail="LLD not found.")

    for key, value in updated.dict().items():
        setattr(lld, key, value)

    db.commit()
    db.refresh(lld)
    return lld


# Delete LLD
@router.delete("/{link_id}")
def delete_lld(link_id: str, db: Session = Depends(get_db)):
    lld = db.query(LLD).filter(LLD.link_id == link_id).first()
    if not lld:
        raise HTTPException(status_code=404, detail="LLD not found.")

    db.delete(lld)
    db.commit()
    return {"detail": "LLD deleted successfully"}
