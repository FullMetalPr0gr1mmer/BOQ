from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from Database.session import Base

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer , primary_key=True,index=True)
    site_id=Column(String(100), unique=True,index=True)
    site_name=Column(String(100),unique=True,index=True)
    project_id=Column(String(200),ForeignKey("projects.pid_po"),index=True)
