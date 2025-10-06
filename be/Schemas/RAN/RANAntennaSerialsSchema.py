from pydantic import BaseModel
from typing import Optional, List


class RANAntennaSerialsBase(BaseModel):
    mrbts: Optional[str] = None
    antenna_model: Optional[str] = None
    serial_number: Optional[str] = None
    project_id: Optional[str] = None


class RANAntennaSerialsCreate(RANAntennaSerialsBase):
    pass


class RANAntennaSerialsUpdate(RANAntennaSerialsBase):
    pass


class RANAntennaSerialsOut(RANAntennaSerialsBase):
    id: int

    class Config:
        from_attributes = True


class PaginatedRANAntennaSerials(BaseModel):
    records: List[RANAntennaSerialsOut]
    total: int
