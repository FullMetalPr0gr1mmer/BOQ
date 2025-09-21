# Schemas/RopPackageSchema.py - Updated version
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import date
from .MonthlyDistributionSchema import MonthlyDistributionItem, MonthlyDistributionOut


class RopPackageCreate(BaseModel):
    project_id: str
    package_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    quantity: Optional[int] = None
    lvl1_ids: List[dict] = []  # list of Lvl1 IDs to associate
    price: Optional[float] = None
    lead_time: Optional[int] = None
    monthly_distributions: Optional[List[MonthlyDistributionItem]] = []

    @validator('monthly_distributions')
    def validate_monthly_distributions(cls, v, values):
        if not v:
            return v

        # Check if total quantity matches package quantity
        if 'quantity' in values and values['quantity'] is not None:
            total_distributed = sum(item.quantity for item in v)
            if total_distributed != values['quantity']:
                raise ValueError(
                    f'Total distributed quantity ({total_distributed}) must equal package quantity ({values["quantity"]})')

        # Check for duplicate month-year combinations
        month_year_pairs = [(item.year, item.month) for item in v]
        if len(month_year_pairs) != len(set(month_year_pairs)):
            raise ValueError('Duplicate month-year combinations found in distributions')

        return v


class RopPackageUpdate(BaseModel):
    package_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    lvl1_ids: Optional[List[dict]] = None
    quantity: Optional[int] = None
    lead_time: Optional[int] = None
    price: Optional[float] = None
    monthly_distributions: Optional[List[MonthlyDistributionItem]] = None

    @validator('monthly_distributions')
    def validate_monthly_distributions(cls, v, values):
        if v is None:
            return v

        if not v:
            return v

        # Check for duplicate month-year combinations
        month_year_pairs = [(item.year, item.month) for item in v]
        if len(month_year_pairs) != len(set(month_year_pairs)):
            raise ValueError('Duplicate month-year combinations found in distributions')

        return v


class RopPackageOut(BaseModel):
    id: int
    project_id: str
    package_name: str
    start_date: Optional[date]
    end_date: Optional[date]
    lvl1_items: List[dict]  # just return list of item_names or IDs
    quantity: Optional[int] = None
    price: Optional[float] = None
    lead_time: Optional[int] = None
    monthly_distributions: List[MonthlyDistributionOut] = []

    class Config:
        from_attributes = True