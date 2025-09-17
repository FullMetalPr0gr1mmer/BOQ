from sqlalchemy import Column, Integer, String, ForeignKey
from Database.session import Base


class RAN_LLD(Base):
    __tablename__ = "ran_lld"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_id = Column(String(100), index=True, nullable=False)
    new_antennas = Column(String, nullable=True)
    total_antennas = Column(Integer, nullable=True)
    technical_boq = Column(String(255), nullable=True)
    key = Column(String(200),nullable=True)
    pid_po = Column(String(200),ForeignKey('ran_projects.pid_po'), index=True, nullable=True)
