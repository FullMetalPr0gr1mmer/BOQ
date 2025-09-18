# Models/ROPProject.py

from sqlalchemy import Enum as SQLAlchemyEnum, String, Column,Integer
from Database.session import Base
from enum import Enum

class ROPProject(Base):
    __tablename__ = 'rop_projects'
    pid_po = Column(String(200), primary_key=True, index=True)
    pid = Column(String(100), index=True)
    po = Column(String(100), index=True)
    project_name = Column(String(200), index=True)
    wbs = Column(String(200), index=True)
    country = Column(String(200), index=True)
    currency = Column(String(200),default='Euros', index=True)
    product_number = Column(String(100),nullable=True, index=True)
