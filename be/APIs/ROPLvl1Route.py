import json
from typing import List

from fastapi import Depends, HTTPException, APIRouter
from starlette import status

from APIs.Core import get_db
from Database.session import Session
from Models.ROPLvl1 import ROPLvl1, ROPLvl1Distribution
from Schemas.ROPLvl1Schema import ROPLvl1Out, ROPLvl1Create

ROPLvl1router = APIRouter(prefix="/rop-lvl1", tags=["ROP Lvl1"])


# Create Lvl1 + nested distributions
@ROPLvl1router.post("/create", response_model=ROPLvl1Out)
def create_lvl1(data: ROPLvl1Create, db: Session = Depends(get_db)):
    new_lvl1 = ROPLvl1(
        project_id=data.project_id,
        project_name=data.project_name,
        item_name=data.item_name,
        region=data.region,
        total_quantity=data.total_quantity,
        price=data.price,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(new_lvl1)
    db.commit()
    db.refresh(new_lvl1)

    for dist in data.distributions:
        distribution = ROPLvl1Distribution(
            lvl1_id=new_lvl1.id,
            year=dist.year,
            month=dist.month,
            allocated_quantity=dist.allocated_quantity
        )
        db.add(distribution)
    db.commit()

    db.refresh(new_lvl1)
    return new_lvl1


# Get all Lvl1 records
@ROPLvl1router.get("/", response_model=List[ROPLvl1Out])
def get_all_lvl1(db: Session = Depends(get_db)):
    lvl1_list = db.query(ROPLvl1).all()
    return lvl1_list


# Get single Lvl1 by ID
@ROPLvl1router.get("/{id}", response_model=ROPLvl1Out)
def get_lvl1_by_id(id: int, db: Session = Depends(get_db)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")

    return lvl1


# Update a Lvl1 entry
@ROPLvl1router.put("/update/{id}", response_model=ROPLvl1Out)
def update_lvl1(id: int, data: ROPLvl1Create, db: Session = Depends(get_db)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")

    # Update main fields
    lvl1.project_id = data.project_id
    lvl1.project_name = data.project_name
    lvl1.item_name = data.item_name
    lvl1.region = data.region
    lvl1.total_quantity = data.total_quantity
    lvl1.price = data.price
    lvl1.start_date = data.start_date
    lvl1.end_date = data.end_date

    # Delete old distributions
    db.query(ROPLvl1Distribution).filter(ROPLvl1Distribution.lvl1_id == id).delete()

    # Add new distributions
    for dist in data.distributions:
        new_dist = ROPLvl1Distribution(
            lvl1_id=id,
            year=dist.year,
            month=dist.month,
            allocated_quantity=dist.allocated_quantity
        )
        db.add(new_dist)

    db.commit()
    db.refresh(lvl1)
    return lvl1


# Delete a Lvl1 entry and its distributions
@ROPLvl1router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lvl1(id: int, db: Session = Depends(get_db)):
    lvl1 = db.query(ROPLvl1).filter(ROPLvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    db.delete(lvl1)
    db.commit()
