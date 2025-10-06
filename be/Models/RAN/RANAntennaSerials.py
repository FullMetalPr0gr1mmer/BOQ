from sqlalchemy import Column, Integer, String, ForeignKey
from Database.session import Base


class RANAntennaSerials(Base):
    __tablename__ = "ran_antenna_serials"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mrbts = Column(String(200), nullable=True)
    antenna_model = Column(String(200), nullable=True)
    serial_number = Column(String(200), nullable=True)
    project_id = Column(String(200), ForeignKey('ran_projects.pid_po'), index=True, nullable=True)
