# Schemas/ROPLvl2Schema.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class ROPLvl2DistributionCreate(BaseModel):
    year: int
    month: int
    allocated_quantity: int

class ROPLvl2Create(BaseModel):
    id: str
    project_id: str
    lvl1_id: str
    lvl1_item_name: str
    item_name: str
    region: str
    total_quantity: int
    price: float
    start_date: date
    end_date: date
    product_number: Optional[str] = None
    distributions: List[ROPLvl2DistributionCreate]

class ROPLvl2DistributionOut(ROPLvl2DistributionCreate):
    id: int
    class Config:
        orm_mode = True

class ROPLvl2Out(BaseModel):
    id: str
    project_id: str
    lvl1_id: str
    lvl1_item_name: str
    item_name: str
    region: str
    total_quantity: int
    price: float
    start_date: date
    end_date: date
    product_number: str
    distributions: List[ROPLvl2DistributionOut]
    class Config:
        orm_mode = True
