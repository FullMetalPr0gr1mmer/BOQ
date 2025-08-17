# Schemas/ROPProjectSchema.py
from pydantic import BaseModel, Field
from typing import Optional
from Models.ROPProject import CurrencyEnum

class ROPProjectBase(BaseModel):
    pid: str
    po: str
    project_name: str
    product_number: Optional[str] = None
    wbs: str                      # renamed here
    country: Optional[str] = None
    currency: CurrencyEnum = Field(default=CurrencyEnum.euros)

class ROPProjectCreate(ROPProjectBase):
    pass

class ROPProjectOut(ROPProjectBase):
    class Config:
        orm_mode = True
