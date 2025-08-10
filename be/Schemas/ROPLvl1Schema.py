# schemas/lvl1.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class ROPLvl1DistributionCreate(BaseModel):
    year: int
    month: int
    allocated_quantity: int


class ROPLvl1Create(BaseModel):
    project_id: str
    project_name: str
    item_name: str
    region: str
    total_quantity: int
    price: int
    start_date: date
    end_date: date
    distributions: List[ROPLvl1DistributionCreate]


class ROPLvl1DistributionOut(ROPLvl1DistributionCreate):
    id: int
    class Config:
        orm_mode = True


class ROPLvl1Out(BaseModel):
    id: int
    project_id: str
    project_name: str
    item_name: str
    region: str
    total_quantity: int
    price: int

    start_date: date
    end_date: date
    distributions: List[ROPLvl1DistributionOut]

    class Config:
        orm_mode = True
class ROPLvl1Update(ROPLvl1Create):
    pass
