from pydantic import BaseModel
from typing import Optional, List


class RANSiteBase(BaseModel):
    site_id: Optional[str] =None
    new_antennas: Optional[str] =None
    total_antennas: Optional[int] =None
    technical_boq: Optional[str] = None
    pid_po: Optional[str] =None
    key:Optional[str] = None

class RANSiteCreate(RANSiteBase):
    pass


class RANSiteUpdate(RANSiteBase):
    pass


class RANSiteOut(RANSiteBase):
    id: int

    class Config:
        orm_mode = True
class PaginatedRANSites(BaseModel):
    records: List[RANSiteOut]
    total: int