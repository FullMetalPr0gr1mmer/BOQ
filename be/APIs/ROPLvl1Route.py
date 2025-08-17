import os
import shutil
from typing import List
from fastapi import Depends, HTTPException, APIRouter, UploadFile, File
from starlette import status
from datetime import date

from starlette.responses import JSONResponse

from APIs.Core import get_db
from Database.session import Session
from Models.ROPLvl1 import ROPLvl1
from Models.ROPLvl2 import ROPLvl2  # for date sync
from Schemas.ROPLvl1Schema import ROPLvl1Out, ROPLvl1Create

ROPLvl1router = APIRouter(prefix="/rop-lvl1", tags=["ROP Lvl1"])

# --- Helper to update Lvl1 start/end dates from Lvl2 ---
def update_lvl1_dates(lvl1_id: int, db: Session):
    lvl2_items = db.query(ROPLvl2).filter(ROPLvl2.lvl1_id == lvl1_id).all()
    if not lvl2_items:
        return
    earliest = min((i.start_date for i in lvl2_items if i.start_date), default=None)
    latest = max((i.end_date for i in lvl2_items if i.end_date), default=None)
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == lvl1_id).first()
    if lvl1:
        lvl1.start_date = earliest
        lvl1.end_date = latest
        db.commit()

# --- Create Lvl1 ---
@ROPLvl1router.post("/create", response_model=ROPLvl1Out)
def create_lvl1(data: ROPLvl1Create, db: Session = Depends(get_db)):
    new_lvl1 = ROPLvl1(**data.dict())
    db.add(new_lvl1)
    db.commit()
    db.refresh(new_lvl1)
    return new_lvl1

# --- Get all ---
@ROPLvl1router.get("/", response_model=List[ROPLvl1Out])
def get_all_lvl1(db: Session = Depends(get_db)):
    return db.query(ROPLvl1).all()

# --- Get by project ---
@ROPLvl1router.get("/by-project/{pid_po}", response_model=List[ROPLvl1Out])
def get_lvl1_by_project(pid_po: str, db: Session = Depends(get_db)):
    return db.query(ROPLvl1).filter(ROPLvl1.project_id == pid_po).all()

# --- Get by ID ---
@ROPLvl1router.get("/{id}", response_model=ROPLvl1Out)
def get_lvl1_by_id(id: int, db: Session = Depends(get_db)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    return lvl1

# --- Update ---
@ROPLvl1router.put("/update/{id}", response_model=ROPLvl1Out)
def update_lvl1(id: int, data: ROPLvl1Create, db: Session = Depends(get_db)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    for field, value in data.dict().items():
        setattr(lvl1, field, value)
    db.commit()
    db.refresh(lvl1)
    return lvl1

# --- Delete ---
@ROPLvl1router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lvl1(id: int, db: Session = Depends(get_db)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    db.delete(lvl1)
    db.commit()


