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
    smp_id = Column(String(200), nullable=True)  # Deprecated - keeping for backward compatibility
    so_number = Column(String(200), nullable=True)  # Deprecated - keeping for backward compatibility

    # New multi-SMP fields
    planning_smp_id = Column(String(200), nullable=True)  # Planning services SMP ID
    planning_so_number = Column(String(200), nullable=True)  # Planning services SO# from PO Report
    implementation_smp_id = Column(String(200), nullable=True)  # Implementation services SMP ID
    implementation_so_number = Column(String(200), nullable=True)  # Implementation services SO# from PO Report
    dismantling_smp_id = Column(String(200), nullable=True)  # Dismantling services SMP ID (MW only)
    dismantling_so_number = Column(String(200), nullable=True)  # Dismantling services SO# from PO Report (MW only)
    epac_req = Column(String(200), nullable=True)  # E-PAC Req value
    inservice_date = Column(String(200), nullable=True)  # InService Date value

    triggering_file_path = Column(String(500), nullable=True)  # Generated triggering CSV
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = relationship("User", foreign_keys=[uploaded_by])