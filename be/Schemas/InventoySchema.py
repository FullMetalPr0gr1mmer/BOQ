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
    mnemonic : str
    clei_code : str
    part_no : str
    software_no : str
    factory_id : str
    serial_no : str
    date_id : str
    manufactured_date : str
    customer_field : str
    license_points_consumed : str
    alarm_status : str
    Aggregated_alarm_status : str
class GetInventory(CreateInventory):
    id:int
class Config:
    orm_mode = True
