from sqlalchemy import String, Column, Integer
from Database.session import Base


class NDPDData(Base):
    __tablename__ = 'ndpd_data'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    period = Column(String(50), nullable=False, index=True)
    ct = Column(String(500), nullable=False, index=True)
    actual_sites = Column(Integer, nullable=False, default=0)
    forecast_sites = Column(Integer, nullable=False, default=0)
