from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from Database.session import Base

class ROPLvl2(Base):
    __tablename__ = "rop_lvl2"
    id = Column(String(200), primary_key=True, index=True)
    project_id = Column(String(200), ForeignKey("rop_projects.pid_po"), index=True)
    lvl1_id = Column(String(200), ForeignKey("rop_lvl1.id"), index=True)
    lvl1_item_name = Column(String(200))
    item_name = Column(String(200))
    region = Column(String(100))
    total_quantity = Column(Integer)
    product_number = Column(String(100),nullable=True, index=True)
    price = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)

    # Back-reference to lvl1
    lvl1 = relationship("ROPLvl1", back_populates="lvl2_items")

    distributions = relationship("ROPLvl2Distribution", back_populates="rop_lvl2", cascade="all, delete-orphan")

class ROPLvl2Distribution(Base):
    __tablename__ = "rop_lvl2_distribution"

    id = Column(Integer, primary_key=True, index=True)
    lvl2_id = Column(String(200), ForeignKey('rop_lvl2.id', ondelete="CASCADE"))
    year = Column(Integer)
    month = Column(Integer)
    allocated_quantity = Column(Integer)

    rop_lvl2 = relationship("ROPLvl2", back_populates="distributions")
