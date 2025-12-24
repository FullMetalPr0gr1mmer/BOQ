from pydantic import BaseModel
from typing import List, Optional


class CreateNDPDData(BaseModel):
    """Schema for creating a new NDPD Data record."""
    period: str
    ct: str
    actual_sites: int
    forecast_sites: int


class UpdateNDPDData(BaseModel):
    """Schema for updating an existing NDPD Data record."""
    period: Optional[str] = None
    ct: Optional[str] = None
    actual_sites: Optional[int] = None
    forecast_sites: Optional[int] = None


class NDPDDataOut(BaseModel):
    """Schema for returning an NDPD Data record."""
    id: int
    period: str
    ct: str
    actual_sites: int
    forecast_sites: int

    class Config:
        from_attributes = True


class NDPDDataPagination(BaseModel):
    """Schema for paginated NDPD Data responses."""
    records: List[NDPDDataOut]
    total: int

    class Config:
        from_attributes = True
