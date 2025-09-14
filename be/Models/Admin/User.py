from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from Database.session import Base
from .AuditLog import AuditLog  # Correctly import the AuditLog model


# Define the Role and User classes together to resolve the relationship dependency
class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)

    # This is the "one" side of the one-to-many relationship with User
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String)
    registered_at = Column(DateTime, default=datetime.now())

    # This is the foreign key column that holds the ID of the related role
    role_id = Column(Integer, ForeignKey('roles.id'))

    # This is the "many" side of the relationship, linking back to Role
    role = relationship("Role", back_populates="users")

    # Relationship to AuditLog
    audit_logs = relationship("AuditLog", back_populates="user", lazy="dynamic")


class UserProjectAccess(Base):
    __tablename__ = 'user_project_access'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    project_id = Column(String(200), ForeignKey('projects.pid_po'), nullable=False)
    permission_level = Column(String(50), nullable=False, default="view")