# Models/LE/MonthlyDistribution.py
from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from Database.session import Base


class MonthlyDistribution(Base):
    __tablename__ = "monthly_distributions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("rop_packages.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    quantity = Column(Integer, nullable=False, default=0)

    # Relationship back to package
    package = relationship("RopPackage", back_populates="monthly_distributions")

    class Config:
        # Ensure unique combination of package_id, year, month
        __table_args__ = (
            {'extend_existing': True}
        )