from pydantic import BaseModel
from typing import Optional
from datetime import date

class ROPLvl1Base(BaseModel):
    id:int
    project_id: str
    project_name: str
    item_name: str
    region: Optional[str] = None
    total_quantity: Optional[int] = None
    price: Optional[float] = None
    product_number: Optional[str] = None
class ROPLvl1Create(ROPLvl1Base):
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ROPLvl1Out(ROPLvl1Base):
    id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    class Config:
        from_attributes = True
