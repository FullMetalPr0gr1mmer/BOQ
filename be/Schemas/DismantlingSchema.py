from pydantic import BaseModel
from typing import Optional, List


class DismantlingBase(BaseModel):
    nokia_link_id: str
    nec_dismantling_link_id: str
    no_of_dismantling: int
    comments: Optional[str] = None

class DismantlingCreate(DismantlingBase):
    pass

class DismantlingUpdate(DismantlingBase):
    pass

class DismantlingOut(DismantlingBase):
    id: int

    class Config:
        orm_mode = True


class DismantlingPagination(BaseModel):
    records: List[DismantlingOut]
    total: int

    class Config:
        orm_mode = True