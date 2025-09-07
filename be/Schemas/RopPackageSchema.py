# Schemas/RopPackageSchema.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class RopPackageCreate(BaseModel):
    project_id: str
    package_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    quantity: Optional[int] = None
    lvl1_ids: List[dict] = []  # list of Lvl1 IDs to associate
    price: Optional[float] = None
class RopPackageUpdate(BaseModel):
    package_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    lvl1_ids: Optional[List[dict]] = None  # optional for updates
    quantity: Optional[int] = None

class RopPackageOut(BaseModel):
    id: int
    project_id: str
    package_name: str
    start_date: Optional[date]
    end_date: Optional[date]
    lvl1_items: List[dict]  # just return list of item_names or IDs
    quantity: Optional[int] = None
    price: Optional[float] = None
    class Config:
        orm_mode = True
