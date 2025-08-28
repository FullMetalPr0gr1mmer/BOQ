from pydantic import BaseModel
from typing import List, Optional

from Models.Levels import TypeofService

class Lvl1Create(BaseModel):
    service_type: List[TypeofService] = []
    project_id: str
    project_name: str
    item_name: str
    region: str
    quantity: int
    price: int

    class Config:
        use_enum_values = True
        orm_mode = True

class Lvl1Out(BaseModel):
    id: int
    project_id: str
    project_name: str
    item_name: str
    region: Optional[str] = None
    quantity: int
    price: int
    service_type: List[str]  # <-- previously List[TypeofService]

    class Config:
        orm_mode = True

#####################################################################################################
################### LEVEL 3####################



# ---------- ItemsForLvl3 ----------
class ItemsForLvl3Base(BaseModel):
    item_name: str
    item_details: Optional[str] = None
    vendor_part_number: Optional[str] = None
    service_type: Optional[List[str]] = None
    category: Optional[str] = None
    uom: Optional[int] = None
    quantity: Optional[int] = None
    price: Optional[int] = None


class ItemsForLvl3Create(ItemsForLvl3Base):
    pass


class ItemsForLvl3Out(ItemsForLvl3Base):
    id: int

    class Config:
        orm_mode = True


# ---------- Lvl3 ----------
class Lvl3Base(BaseModel):
    project_id: str
    project_name: str
    item_name: str
    service_type: Optional[List[str]] = None
    uom: Optional[str] = None
    total_quantity: Optional[int] = None
    total_price: Optional[int] = None


class Lvl3Create(Lvl3Base):
    items: List[ItemsForLvl3Create] = []


class Lvl3Update(Lvl3Base):
    items: Optional[List[ItemsForLvl3Create]] = None


class Lvl3Out(Lvl3Base):
    id: int
    items: List[ItemsForLvl3Out] = []

    class Config:
        orm_mode = True
