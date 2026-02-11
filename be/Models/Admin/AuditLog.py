from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from Database.session import Base


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)

    # This is the foreign key column to the users table
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(200), nullable=True)
    resource_name = Column(String(500), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Project tracking for project-scoped access control
    # project_id stores the pid_po of the related project (if applicable)
    project_id = Column(String(200), nullable=True, index=True)
    # section indicates project type: 1=BOQ, 2=RAN, 3=ROP, 4=DU
    section = Column(Integer, nullable=True, index=True)

    # This is the relationship that links to the User model
    user = relationship("User", back_populates="audit_logs")

    # Composite index for efficient project-scoped queries
    __table_args__ = (
        Index('ix_audit_logs_project_section', 'project_id', 'section'),
    )