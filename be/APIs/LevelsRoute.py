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
    result = []
    for entry in entries:
        result.append(Lvl1Out(
            id=entry.id,
            project_id=entry.project_id,
            project_name=entry.project_name,
            item_name=entry.item_name,
            region=entry.region if entry.region else "Main",
            quantity=entry.quantity,
            price=entry.price,
            service_type=entry.get_service_type()
        ))
    return result

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
    result = []
    for item in items:
        result.append(Lvl3ItemsOut(
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
        ))
    return result

# ---------------------------- Dynamic route by ID ----------------------------

@levelsRouter.get("/get-lvl3-by-id/{id}")
def get_lvl3_by_id(id: int, db: Session = Depends(get_db)):
    lvl3_item = db.query(Lvl3).filter(Lvl3.id == id).first()
    if not lvl3_item:
        raise HTTPException(status_code=404, detail="Lvl3 item not found")
    lvl3_item.service_type = lvl3_item.get_service_type()
    return lvl3_item

# ---------------------------- Route by item_name ----------------------------

@levelsRouter.get("/get-lvl3-item-by-name/{'item_name'}", response_model=List[Lvl3ItemsOut])
def get_lvl3_items_by_name( item_name:str ,db: Session = Depends(get_db)):
    #print(f"Searching for item_name: {item_name}")  # Debug log
    items = db.query(ItemsForLvl3).filter(ItemsForLvl3.item_name == item_name).all()

    #if not items:
        # raise HTTPException(status_code=404, detail=f"No items found with item_name: '{item_name}'")

    return [
        Lvl3ItemsOut(
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
        ) for item in items
    ]
