# models/lvl1.py

from sqlalchemy import Column, String, Integer, Date, ForeignKey,Text
from sqlalchemy.orm import relationship
from Database.session import Base

class ROPLvl1(Base):
    __tablename__ = 'rop_lvl1'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(200),ForeignKey("rop_projects.pid_po"), index=True)
    project_name = Column(String(100))
    item_name = Column(String(100))
    region = Column(String(100))
    total_quantity = Column(Integer)
    price = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    distributions = relationship("ROPLvl1Distribution", back_populates="rop_lvl1", cascade="all, delete-orphan")


class ROPLvl1Distribution(Base):
    __tablename__ = 'rop_lvl1_distribution'

    id = Column(Integer, primary_key=True, index=True)
    lvl1_id = Column(Integer, ForeignKey('rop_lvl1.id', ondelete="CASCADE"))
    year = Column(Integer)
    month = Column(Integer)
    allocated_quantity = Column(Integer)

    # This must match the name used in ROPLvl1.relationship(back_populates=...)
    rop_lvl1 = relationship("ROPLvl1", back_populates="distributions")

