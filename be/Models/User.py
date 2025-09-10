from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship  # <-- New import
from Database.session import Base


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    users = relationship("User", back_populates="role")  # <-- New relationship


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String)
    registered_at = Column(DateTime, default=datetime.now())

    # Change 'role' column to a foreign key
    role_id = Column(Integer, ForeignKey('roles.id'))
    role = relationship("Role", back_populates="users")  # <-- New relationship