from pydantic import BaseModel
from typing import Optional


class LLDCreate(BaseModel):
    link_id: str
    action: str
    fon: str
    item_name: str
    distance: str
    scope: str
    fe: str
    ne: str
    link_category: str
    link_status: str
    comments: str
    dismanting_link_id: str
    band: str
    t_band_cs: str
    ne_ant_size: str
    fe_ant_size: str
    sd_ne: str
    sd_fe: str
    odu_type: str
    updated_sb: str
    region: str
    losr_approval: str
    initial_lb: str
    flb: str


class LLDOut(LLDCreate):
    class Config:
        orm_mode = True
