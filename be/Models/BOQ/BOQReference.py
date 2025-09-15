from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
import uuid
from Database.session import Base


class BOQReference(Base):
    __tablename__ = "boq_reference"


    id = Column(String(200), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    linkid = Column(String(200), nullable=False, index=True)
    interface_name = Column(String(200), nullable=True)
    site_ip_a = Column(String(100), nullable=True)
    site_ip_b = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    pid_po = Column(String(200),ForeignKey('projects.pid_po'), nullable=True)