"""
Approval Workflow Model
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from Database.session import Base


class Approval(Base):
    __tablename__ = 'approvals'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    template_filename = Column(String(255), nullable=False)
    template_file_path = Column(String(500), nullable=False)
    project_id = Column(String(200), nullable=False)
    project_type = Column(String(50), nullable=False)
    stage = Column(String(20), nullable=False, default='approval')
    status = Column(String(30), nullable=False, default='pending_approval')
    notes = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = relationship("User", foreign_keys=[uploaded_by])