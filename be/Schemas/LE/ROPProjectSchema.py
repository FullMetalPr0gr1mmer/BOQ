# Schemas/ROPProjectSchema.py
from pydantic import BaseModel, Field
from typing import Optional


class ROPProjectBase(BaseModel):
    pid: str
    po: str
    project_name: str
    product_number: Optional[str] = None
    wbs: str                      # renamed here
    country: Optional[str] = None
    currency: str = Field(default='Euros')

class ROPProjectCreate(ROPProjectBase):
    pass

class ROPProjectOut(ROPProjectBase):
    pid_po:str


    class Config:
        orm_mode = True
