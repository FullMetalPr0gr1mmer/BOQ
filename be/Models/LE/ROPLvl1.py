from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from Database.session import Base

class ROPLvl1(Base):
    __tablename__ = "rop_lvl1"

    id = Column(String(200), primary_key=True, index=True)
    project_id = Column(String(200), ForeignKey("rop_projects.pid_po"), nullable=False)
    project_name = Column(String(100), nullable=False)
    item_name = Column(String(100), nullable=False)
    region = Column(String(100), nullable=True)
    total_quantity = Column(Integer, nullable=True)
    # New: sum of total quantities across all packages this lvl1 is linked to
    consumption = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    product_number = Column(String(100), nullable=True, index=True)

    # Existing relationship to Lvl2
    lvl2_items = relationship("ROPLvl2", back_populates="lvl1")

    # Many-to-many relationship with RopPackage
    packages = relationship(
        "RopPackage",
        secondary="rop_package_lvl1",
        back_populates="lvl1_items"
    )
