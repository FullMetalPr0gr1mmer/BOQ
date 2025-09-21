# Schemas/LE/MonthlyDistributionSchema.py
from pydantic import BaseModel, validator
from typing import List, Optional, Dict
from datetime import date


class MonthlyDistributionItem(BaseModel):
    year: int
    month: int  # 1-12
    quantity: int

    @validator('month')
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError('Month must be between 1 and 12')
        return v

    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 0:
            raise ValueError('Quantity must be non-negative')
        return v


class MonthlyDistributionOut(MonthlyDistributionItem):
    id: int
    package_id: int

    class Config:
        from_attributes = True