from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from Database.session import Base
class Project(Base):
    __tablename__ = 'projects'
    pid_po=Column(String(200), primary_key=True,index=True)
    pid=Column(String(100), index=True)
    po=Column(String(100), index=True)
    project_name=Column(String(200), index=True)


