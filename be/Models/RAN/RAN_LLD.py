from sqlalchemy import Column, Integer, String
from Database.session import Base


class RAN_LLD(Base):
    __tablename__ = "ran_lld"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_id = Column(String(100), index=True, nullable=False)
    new_antennas = Column(String, nullable=True)
    total_antennas = Column(Integer, nullable=True)
    technical_boq = Column(String(255), nullable=True)
    key = Column(Integer,nullable=True)
