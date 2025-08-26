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
    lvl1_ids: List[str] = []  # list of Lvl1 IDs to associate

class RopPackageUpdate(BaseModel):
    package_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    lvl1_ids: Optional[List[str]] = None  # optional for updates
    quantity: Optional[int] = None

class RopPackageOut(BaseModel):
    id: int
    project_id: str
    package_name: str
    start_date: Optional[date]
    end_date: Optional[date]
    lvl1_items: List[str]  # just return list of item_names or IDs
    quantity: Optional[int] = None

    class Config:
        orm_mode = True
