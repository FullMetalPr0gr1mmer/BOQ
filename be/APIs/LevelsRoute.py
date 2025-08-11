from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from APIs.Core import get_db
from Models.Levels import Lvl1, Lvl3, ItemsForLvl3
from Schemas.LevelsSchema import (
    Lvl1Create, Lvl1Out,
    Lvl3Create, Lvl3ItemsCreate, Lvl3ItemsOut
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

# ---------------------------- Level 3 ----------------------------

@levelsRouter.post("/create-lvl3")
def create_lvl3(data: Lvl3Create, db: Session = Depends(get_db)):
    db_lvl3 = Lvl3(
        project_id=data.project_id,
        project_name=data.project_name,
        item_name=data.item_name,
        uom=data.uom,
        total_quantity=data.total_quantity,
        total_price=data.total_price
    )
    db_lvl3.set_service_type(data.service_type)
    db.add(db_lvl3)
    db.commit()
    db.refresh(db_lvl3)
    return db_lvl3

@levelsRouter.get("/get-lvl3")
def get_all_lvl3(db: Session = Depends(get_db)):
    lvl3_items = db.query(Lvl3).all()
    for item in lvl3_items:
        item.service_type = item.get_service_type()
    return lvl3_items

@levelsRouter.put("/update-lvl3/{id}")
def update_lvl3(id: int, data: Lvl3Create, db: Session = Depends(get_db)):
    lvl3 = db.query(Lvl3).filter(Lvl3.id == id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 entry not found")
    lvl3.project_id = data.project_id
    lvl3.project_name = data.project_name
    lvl3.item_name = data.item_name
    lvl3.uom = data.uom
    lvl3.total_quantity = data.total_quantity
    lvl3.total_price = data.total_price
    lvl3.set_service_type(data.service_type)
    db.commit()
    db.refresh(lvl3)
    return lvl3

@levelsRouter.delete("/delete-lvl3/{id}")
def delete_lvl3(id: int, db: Session = Depends(get_db)):
    lvl3 = db.query(Lvl3).filter(Lvl3.id == id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 entry not found")
    db.delete(lvl3)
    db.commit()
    return {"msg": "Lvl3 entry deleted"}

# ---------------------------- Level 3 Items ----------------------------

@levelsRouter.post("/create-lvl3-item")
def create_lvl3_item(data: Lvl3ItemsCreate, db: Session = Depends(get_db)):
    item = ItemsForLvl3(
        project_id=data.project_id,
        item_name=data.item_name,
        item_details=data.item_details,
        vendor_part_number=data.vendor_part_number,
        category=data.category,
        uom=data.uom,
        quantity=data.quantity,
        price=data.price,
    )
    item.set_service_type(data.service_type)
    db.add(item)
    db.commit()
    db.refresh(item)
    return Lvl3ItemsOut(
        id=item.id,
        project_id=item.project_id,
        item_name=item.item_name,
        item_details=item.item_details,
        vendor_part_number=item.vendor_part_number,
        category=item.category,
        uom=item.uom,
        quantity=item.quantity,
        price=item.price,
        service_type=item.get_service_type()
    )

@levelsRouter.get("/get-lvl3-items", response_model=List[Lvl3ItemsOut])
def get_all_lvl3_items(db: Session = Depends(get_db)):
    items = db.query(ItemsForLvl3).all()
    return [
        Lvl3ItemsOut(
            id=item.id,
            project_id=item.project_id,
            item_name=item.item_name,
            item_details=item.item_details,
            vendor_part_number=item.vendor_part_number,
            service_type=item.get_service_type(),
            category=item.category,
            uom=item.uom,
            quantity=item.quantity,
            price=item.price
        ) for item in items
    ]

@levelsRouter.put("/update-lvl3-item/{id}")
def update_lvl3_item(id: int, data: Lvl3ItemsCreate, db: Session = Depends(get_db)):
    item = db.query(ItemsForLvl3).filter(ItemsForLvl3.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Lvl3 item not found")
    item.project_id = data.project_id
    item.item_name = data.item_name
    item.item_details = data.item_details
    item.vendor_part_number = data.vendor_part_number
    item.category = data.category
    item.uom = data.uom
    item.quantity = data.quantity
    item.price = data.price
    item.set_service_type(data.service_type)
    db.commit()
    db.refresh(item)
    return item

@levelsRouter.delete("/delete-lvl3-item/{id}")
def delete_lvl3_item(id: int, db: Session = Depends(get_db)):
    item = db.query(ItemsForLvl3).filter(ItemsForLvl3.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Lvl3 item not found")
    db.delete(item)
    db.commit()
    return {"msg": "Lvl3 item deleted"}
