from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from APIs.Core import get_db
from Models.Levels import Lvl3, ItemsForLvl3
from Schemas.LevelsSchema import Lvl3Create, Lvl3Out, Lvl3Update, ItemsForLvl3Create, ItemsForLvl3Out

router = APIRouter(prefix="/lvl3", tags=["Lvl3"])


# ---------- CREATE LVL3 ----------
@router.post("/create", response_model=Lvl3Out)
def create_lvl3(payload: Lvl3Create, db: Session = Depends(get_db)):
    lvl3 = Lvl3(
        project_id=payload.project_id,
        project_name=payload.project_name,
        item_name=payload.item_name,
        uom=payload.uom,
        total_quantity=payload.total_quantity,
        total_price=payload.total_price,
    )
    lvl3.service_type = payload.service_type or []

    db.add(lvl3)
    db.commit()
    db.refresh(lvl3)
    return lvl3


# ---------- GET ALL ----------
@router.get("/", response_model=List[Lvl3Out])
def get_all_lvl3(db: Session = Depends(get_db)):
    return db.query(Lvl3).all()


# ---------- GET BY ID ----------
@router.get("/{lvl3_id}", response_model=Lvl3Out)
def get_lvl3_by_id(lvl3_id: int, db: Session = Depends(get_db)):
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")
    return lvl3


# ---------- UPDATE LVL3 ----------
@router.put("/{lvl3_id}", response_model=Lvl3Out)
def update_lvl3(lvl3_id: int, payload: Lvl3Update, db: Session = Depends(get_db)):
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    for field, value in payload.dict(exclude_unset=True).items():
        if field == "service_type":
            lvl3.service_type = value or []
        else:
            setattr(lvl3, field, value)

    db.commit()
    db.refresh(lvl3)
    return lvl3


# ---------- DELETE LVL3 ----------
@router.delete("/{lvl3_id}")
def delete_lvl3(lvl3_id: int, db: Session = Depends(get_db)):
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")
    db.delete(lvl3)
    db.commit()
    return {"detail": "Lvl3 deleted successfully"}


# --- NEW ENDPOINTS FOR ITEMS ---

# ---------- ADD ITEM TO LVL3 ----------
@router.post("/{lvl3_id}/items", response_model=ItemsForLvl3Out)
def add_item_to_lvl3(lvl3_id: int, payload: ItemsForLvl3Create, db: Session = Depends(get_db)):
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    new_item = ItemsForLvl3(
        lvl3_id=lvl3_id,
        item_name=payload.item_name,
        item_details=payload.item_details,
        vendor_part_number=payload.vendor_part_number,
        category=payload.category,
        uom=payload.uom,
        quantity=payload.quantity,
        price=payload.price,
    )
    new_item.service_type = payload.service_type or []

    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


# ---------- BULK ADD ITEMS TO LVL3 ----------
@router.post("/{lvl3_id}/items/bulk", response_model=List[ItemsForLvl3Out])
def bulk_add_items_to_lvl3(lvl3_id: int, items_payload: List[ItemsForLvl3Create], db: Session = Depends(get_db)):
    lvl3 = db.query(Lvl3).filter(Lvl3.id == lvl3_id).first()
    if not lvl3:
        raise HTTPException(status_code=404, detail="Lvl3 not found")

    new_items = []
    for payload in items_payload:
        new_item = ItemsForLvl3(
            lvl3_id=lvl3_id,
            item_name=payload.item_name,
            item_details=payload.item_details,
            vendor_part_number=payload.vendor_part_number,
            category=payload.category,
            uom=payload.uom,
            quantity=payload.quantity,
            price=payload.price,
        )
        new_item.service_type = payload.service_type or []
        new_items.append(new_item)

    db.add_all(new_items)
    db.commit()

    # After adding new items, recalculate total_quantity and total_price for the parent Lvl3 record
    all_items = db.query(ItemsForLvl3).filter(ItemsForLvl3.lvl3_id == lvl3_id).all()
    total_quantity = sum(item.quantity for item in all_items if item.quantity is not None)
    total_price = sum(item.price for item in all_items if item.price is not None)


    db.commit()

    for item in new_items:
        db.refresh(item)
    db.refresh(lvl3)

    return new_items


# ---------- UPDATE ITEM FOR LVL3 ----------
@router.put("/{lvl3_id}/items/{item_id}", response_model=ItemsForLvl3Out)
def update_item_for_lvl3(lvl3_id: int, item_id: int, payload: ItemsForLvl3Create, db: Session = Depends(get_db)):
    item = db.query(ItemsForLvl3).filter(ItemsForLvl3.id == item_id, ItemsForLvl3.lvl3_id == lvl3_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found for this Lvl3")

    for field, value in payload.dict(exclude_unset=True).items():
        if field == "service_type":
            item.service_type = value or []
        else:
            setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


# ---------- DELETE ITEM FOR LVL3 ----------
@router.delete("/{lvl3_id}/items/{item_id}")
def delete_item_for_lvl3(lvl3_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemsForLvl3).filter(ItemsForLvl3.id == item_id, ItemsForLvl3.lvl3_id == lvl3_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found for this Lvl3")

    db.delete(item)
    db.commit()
    return {"detail": "Item deleted successfully"}


# ---------- SEARCH ITEMS ----------
@router.get("/search/items", response_model=List[ItemsForLvl3Out])
def search_items(name: str, db: Session = Depends(get_db)):
    results = db.query(ItemsForLvl3).filter(ItemsForLvl3.item_name.ilike(f"%{name}%")).all()
    return results
