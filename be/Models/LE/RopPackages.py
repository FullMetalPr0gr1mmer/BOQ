# Models/LE/RopPackages.py - Updated version
from sqlalchemy import Date, Float
from sqlalchemy import Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from Database.session import Base


class RopPackage(Base):
    __tablename__ = "rop_packages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String(200), ForeignKey("rop_projects.pid_po"), nullable=False)
    package_name = Column(String(200), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    lead_time = Column(Integer, nullable=True)
    currency = Column(String(20), nullable=True)
    # Many-to-many relationship with Lvl1
    lvl1_items = relationship(
        "ROPLvl1",
        secondary="rop_package_lvl1",
        back_populates="packages"
    )

    # One-to-many relationship with MonthlyDistribution
    monthly_distributions = relationship(
        "MonthlyDistribution",
        back_populates="package",
        cascade="all, delete-orphan"
    )


rop_package_lvl1 = Table(
    "rop_package_lvl1",
    Base.metadata,
    Column("package_id", Integer, ForeignKey("rop_packages.id", ondelete="CASCADE"), primary_key=True),
    Column("lvl1_id", String(200), ForeignKey("rop_lvl1.id", ondelete="CASCADE"), primary_key=True),
    Column("quantity", Integer, nullable=True),
)