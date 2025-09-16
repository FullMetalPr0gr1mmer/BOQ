from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from enum import Enum


class TypeofService(str, Enum):
    Software = "1"
    Hardware = "2"
    Service = "3"


class ItemsForRANLvl3Base(BaseModel):
    item_name: Optional[str] = Field(..., max_length=200)
    item_details: Optional[str] = Field(None, max_length=200)
    vendor_part_number: Optional[str] = Field(None, max_length=200)
    service_type: List[str] = Field(default_factory=list)
    category: Optional[str] = Field(None, max_length=200)
    uom: Optional[int] = None
    quantity: Optional[int] = None
    price: Optional[float] = None


class ItemsForRANLvl3Create(ItemsForRANLvl3Base):
    pass


class ItemsForRANLvl3Update(ItemsForRANLvl3Base):
    pass


class ItemsForRANLvl3InDB(ItemsForRANLvl3Base):
    id: int
    ranlvl3_id: int

    model_config = ConfigDict(from_attributes=True)


class RANLvl3Base(BaseModel):
    project_id: str
    item_name: str
    key: Optional[str] = None
    service_type: List[str] = Field(default_factory=list)
    uom: str
    total_quantity: Optional[int] = None
    total_price: Optional[float] = None
    category: Optional[str] = None
    po_line: Optional[str] = None

class RANLvl3Create(RANLvl3Base):
    items: List[ItemsForRANLvl3Create] = Field(default_factory=list)


class RANLvl3Update(RANLvl3Base):
    items: List[ItemsForRANLvl3Update] = Field(default_factory=list)


class RANLvl3InDB(RANLvl3Base):
    id: int
    items: List[ItemsForRANLvl3InDB] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PaginatedRANLvl3Response(BaseModel):
    total: int
    records: List[RANLvl3InDB]
