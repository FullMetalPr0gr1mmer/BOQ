from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from APIs.Core import get_db
from Models.BOQ.Levels import Lvl1
from Schemas.BOQ.LevelsSchema import (
    Lvl1Create, Lvl1Out,
)

levelsRouter = APIRouter(tags=["Levels"])

# ---------------------------- Level 1 ----------------------------

@levelsRouter.post("/create-lvl1")
def create_lvl1_entry(data: Lvl1Create, db: Session = Depends(get_db)):
    lvl1 = Lvl1(
        project_id=data.project_id,
        project_name=data.project_name,
        item_name=data.item_name,
        region=data.region,
        quantity=data.quantity,
        price=data.price
    )
    lvl1.set_service_type(data.service_type)
    db.add(lvl1)
    db.commit()
    db.refresh(lvl1)
    return lvl1

@levelsRouter.get("/get-lvl1")
def get_all_lvl1(db: Session = Depends(get_db)):
    entries = db.query(Lvl1).all()
    return [
        Lvl1Out(
            id=entry.id,
            project_id=entry.project_id,
            project_name=entry.project_name,
            item_name=entry.item_name,
            region=entry.region if entry.region else "Main",
            quantity=entry.quantity,
            price=entry.price,
            service_type=entry.get_service_type()
        )
        for entry in entries
    ]

@levelsRouter.put("/update-lvl1/{id}")
def update_lvl1(id: int, data: Lvl1Create, db: Session = Depends(get_db)):
    lvl1 = db.query(Lvl1).filter(Lvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    lvl1.project_id = data.project_id
    lvl1.project_name = data.project_name
    lvl1.item_name = data.item_name
    lvl1.region = data.region
    lvl1.quantity = data.quantity
    lvl1.price = data.price
    lvl1.set_service_type(data.service_type)
    db.commit()
    db.refresh(lvl1)
    return lvl1

@levelsRouter.delete("/delete-lvl1/{id}")
def delete_lvl1(id: int, db: Session = Depends(get_db)):
    lvl1 = db.query(Lvl1).filter(Lvl1.id == id).first()
    if not lvl1:
        raise HTTPException(status_code=404, detail="Lvl1 entry not found")
    db.delete(lvl1)
    db.commit()
    return {"msg": "Lvl1 entry deleted"}
