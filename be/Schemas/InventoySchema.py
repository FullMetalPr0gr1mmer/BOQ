from typing import List, Optional

from fastapi import Form
from pydantic import BaseModel,EmailStr
from sqlalchemy import Integer, DateTime

class AddSite(BaseModel):
    site_id: str
    site_name: str
    pid_po: str
class CreateInventory(BaseModel):
    site_id: str
    site_name: str
    slot_id: int
    port_id: int
    status: str
    company_id : str
    mnemonic : Optional[str]
    clei_code : Optional[str]
    part_no : Optional[str]
    software_no : str
    factory_id : Optional[str]
    serial_no : str
    date_id : Optional[str]
    manufactured_date : Optional[str]
    customer_field : Optional[str]
    license_points_consumed : Optional[str]
    alarm_status : Optional[str]
    Aggregated_alarm_status : Optional[str]
class GetInventory(CreateInventory):
    id:int
class Config:
    orm_mode = True
# Pydantic models for refactoring
class InventoryOut(CreateInventory):
    id: int
    class Config:
        orm_mode = True

class InventoryPagination(BaseModel):
    records: List[InventoryOut]
    total: int
    class Config:
        orm_mode = True