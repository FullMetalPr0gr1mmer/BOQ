from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from Database.session import Base

class LLD(Base):
    __tablename__ = 'lld'
    id = Column(Integer, primary_key=True,index=True)
    link_id=Column(String(200),index=True)
    action=Column(String(100),index=True)
    fon=Column(String(100),index=True)
    item_name = Column(String(200), index=True)
    distance = Column(String(100),index=True)
    scope = Column(String(100),index=True)
    fe=Column(String(100),index=True)
    ne=Column(String(100),index=True)
    link_category=Column(String(100),index=True)
    link_status=Column(String(100),index=True)
    comments=Column(String(100),index=True)
    dismanting_link_id=Column(String(100),index=True)
    band=Column(String(100),index=True)
    t_band_cs=Column(String(100),index=True)
    ne_ant_size=Column(String(100),index=True)
    fe_ant_size=Column(String(100),index=True)
    sd_ne=Column(String(100),index=True)
    sd_fe=Column(String(100),index=True)
    odu_type=Column(String(100),index=True)
    updated_sb=Column(String(100),index=True)
    region=Column(String(100),index=True)
    losr_approval=Column(String(100),index=True)
    initial_lb=Column(String(100),index=True)
    flb=Column(String(100),index=True)

