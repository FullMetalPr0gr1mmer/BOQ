from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from APIs.Core import get_db
from APIs.ROPLvl1Route import get_lvl1_by_id, update_lvl1
from Models.ROPLvl2 import ROPLvl2, ROPLvl2Distribution
from Schemas.ROPLvl2Schema import ROPLvl2Create, ROPLvl2Out

ROPLvl2router = APIRouter(prefix="/rop-lvl2", tags=["ROP Lvl2"])

# CREATE Lvl2 + distributions
@ROPLvl2router.post("/create", response_model=ROPLvl2Out)
def create_lvl2(data: ROPLvl2Create, db: Session = Depends(get_db)):
    new_lvl2 = ROPLvl2(**data.dict(exclude={"distributions"}))
    db.add(new_lvl2)
    db.commit()
    db.refresh(new_lvl2)

    for dist in data.distributions:
        distribution = ROPLvl2Distribution(
            lvl2_id=new_lvl2.id,
            month=dist.month,
            year=dist.year,
            allocated_quantity=dist.allocated_quantity
        )
        db.add(distribution)
    db.commit()
    db.refresh(new_lvl2)
    roplvl1_data=get_lvl1_by_id(new_lvl2.lvl1_id,db=db)
    roplvl1_data.price=(roplvl1_data.price+((new_lvl2.price*new_lvl2.total_quantity)/roplvl1_data.total_quantity))
    return new_lvl2

# READ ALL
@ROPLvl2router.get("/", response_model=List[ROPLvl2Out])
def get_all_lvl2(db: Session = Depends(get_db)):
    return db.query(ROPLvl2).all()

# READ BY LVL1
@ROPLvl2router.get("/by-lvl1/{lvl1_id}", response_model=List[ROPLvl2Out])
def get_lvl2_by_lvl1(lvl1_id: int, db: Session = Depends(get_db)):
    return db.query(ROPLvl2).filter(ROPLvl2.lvl1_id == lvl1_id).all()

# READ ONE
@ROPLvl2router.get("/{id}", response_model=ROPLvl2Out)
def get_lvl2_by_id(id: int, db: Session = Depends(get_db)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    return lvl2

# UPDATE
@ROPLvl2router.put("/update/{id}", response_model=ROPLvl2Out)
def update_lvl2(id: int, data: ROPLvl2Create, db: Session = Depends(get_db)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")

    for key, value in data.dict(exclude={"distributions"}).items():
        setattr(lvl2, key, value)

    # Update distributions
    db.query(ROPLvl2Distribution).filter(ROPLvl2Distribution.lvl2_id == id).delete()
    for dist in data.distributions:
        db.add(ROPLvl2Distribution(
            lvl2_id=id,
            month=dist.month,
            year=dist.year,
            allocated_quantity=dist.allocated_quantity
        ))

    db.commit()
    db.refresh(lvl2)
    return lvl2

# DELETE
@ROPLvl2router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lvl2(id: int, db: Session = Depends(get_db)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    db.delete(lvl2)
    db.commit()
