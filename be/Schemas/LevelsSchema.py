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
class Lvl3Create(BaseModel):
    service_type: List[TypeofService] = []
    project_id: str
    project_name: str
    item_name: str
    uom: str
    total_quantity: int
    total_price: int


    class Config:
        use_enum_values = True
        orm_mode = True

class Lvl3Out(Lvl3Create):
    id: int
    service_type: List[str]
    class Config:
        orm_mode = True



class Lvl3ItemsCreate(BaseModel):
    project_id:str
    item_name:str
    item_details:str
    vendor_part_number:str
    service_type:List[TypeofService] = []
    category:str
    uom:int
    quantity:int
    price:int
    class Config:
        use_enum_values = True
        orm_mode = True

class Lvl3ItemsOut(Lvl3ItemsCreate):
    id: int
    service_type: List[str]
    class Config:
        orm_mode = True
        use_enum_values = True

