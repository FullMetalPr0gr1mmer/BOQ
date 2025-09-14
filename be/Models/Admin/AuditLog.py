from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from Database.session import Base


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)

    # This is the foreign key column to the users table
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(200), nullable=True)
    resource_name = Column(String(500), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # This is the relationship that links to the User model
    user = relationship("User", back_populates="audit_logs")