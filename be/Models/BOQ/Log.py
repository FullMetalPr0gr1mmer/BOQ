from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from Database.session import Base
class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True,index=True)
    user = Column(String(100),ForeignKey("users.username") , index=True)
    log =Column(String(100),index=True)
    timestamp = Column(DateTime,index=True,default=datetime.now())