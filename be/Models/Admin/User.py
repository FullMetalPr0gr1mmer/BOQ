"""
User and Role Management Models

This module defines the core user authentication and authorization models
for the BOQ management system. It includes user accounts, role-based access
control, and project-specific permissions.

Key Models:
1. Role - Defines user roles (admin, user, etc.)
2. User - User account information and authentication
3. UserProjectAccess - Project-specific user permissions

Database Tables:
- roles: User role definitions
- users: User account information
- user_project_access: Project-specific access control

Author: [Your Name]
Created: [Date]
Last Modified: [Date]
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from Database.session import Base
from .AuditLog import AuditLog  # Import AuditLog model for relationship


class Role(Base):
    """
    Role Model - Defines user roles and permissions.

    This model stores role definitions that determine what actions
    users can perform within the system.

    Attributes:
        id (int): Primary key, auto-incrementing
        name (str): Unique role name (e.g., 'admin', 'user', 'viewer')
                   Max length: 100 characters

    Relationships:
        users: One-to-many relationship with User model
               A role can be assigned to multiple users

    Common Roles:
        - admin: Full system access and administration
        - user: Standard user with project access
        - viewer: Read-only access to assigned projects

    Usage Example:
        admin_role = Role(name="admin")
        user_role = Role(name="user")
    """
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)

    # Relationship: One role can have many users
    users = relationship("User", back_populates="role")


class User(Base):
    """
    User Model - Represents system users with authentication and authorization.

    This model stores user account information, authentication credentials,
    and links to roles for permission management.

    Attributes:
        id (int): Primary key, auto-incrementing
        username (str): Unique username for login
                       Max length: 100 characters
        email (str): Unique email address
                    Max length: 100 characters
        hashed_password (str): Bcrypt hashed password (never store plain text)
        registered_at (datetime): Account creation timestamp
        role_id (int): Foreign key linking to Role model

    Relationships:
        role: Many-to-one relationship with Role model
              Each user has exactly one role
        audit_logs: One-to-many relationship with AuditLog model
                   Tracks user actions for audit purposes

    Security Features:
        - Passwords are stored as bcrypt hashes
        - Unique constraints on username and email
        - Role-based access control
        - Audit trail for user actions

    Usage Example:
        user = User(
            username="john_doe",
            email="john@company.com",
            hashed_password=bcrypt_hash,
            role_id=user_role.id
        )
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String)  # Always store hashed passwords
    registered_at = Column(DateTime, default=datetime.now)  # Use callable, not evaluated value

    # Foreign key to Role model
    role_id = Column(Integer, ForeignKey('roles.id'))

    # Approval workflow stage access permissions
    can_access_approval = Column(Boolean, default=False, nullable=False)
    can_access_triggering = Column(Boolean, default=False, nullable=False)
    can_access_logistics = Column(Boolean, default=False, nullable=False)

    # Relationships
    role = relationship("Role", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="dynamic")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class UserProjectAccess(Base):
    """
    User Project Access Model - Manages project-specific user permissions.

    This model provides fine-grained access control by defining which projects
    a user can access and what level of permissions they have for each project.

    Attributes:
        id (int): Primary key, auto-incrementing
        user_id (int): Foreign key to User model
        project_id (str): Foreign key to BOQ projects table (optional)
        permission_level (str): Level of access (view, edit, admin)
                               Default: "view"
        Ranproject_id (str): Foreign key to RAN projects table (optional)
        Ropproject_id (str): Foreign key to ROP projects table (optional)

    Permission Levels:
        - view: Read-only access to project data
        - edit: Can modify project data
        - admin: Full control over project (edit, delete, manage users)

    Project Types:
        - BOQ Projects: Standard Bill of Quantities projects
        - RAN Projects: Radio Access Network projects
        - ROP Projects: Resource Optimization Planning projects

    Business Logic:
        - A user can have access to multiple projects
        - Different permission levels for different projects
        - Supports all three project types in the system
        - Nullable project IDs allow for flexible access patterns

    Usage Example:
        access = UserProjectAccess(
            user_id=user.id,
            project_id="PRJ001_PO123",
            permission_level="edit"
        )
    """
    __tablename__ = 'user_project_access'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    # Project access for different project types (indexed for fast lookups)
    project_id = Column(String(200), ForeignKey('projects.pid_po'), nullable=True, index=True)        # BOQ projects
    Ranproject_id = Column(String(200), ForeignKey('ran_projects.pid_po'), nullable=True, index=True) # RAN projects
    Ropproject_id = Column(String(200), ForeignKey('rop_projects.pid_po'), nullable=True, index=True) # ROP projects
    DUproject_id = Column(String(200), ForeignKey('du_project.pid_po'), nullable=True, index=True)    # DU projects

    # Permission level for the project access
    permission_level = Column(String(50), nullable=False, default="view")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_user_project_access_user_project', 'user_id', 'project_id'),
        Index('ix_user_project_access_user_ran', 'user_id', 'Ranproject_id'),
        Index('ix_user_project_access_user_rop', 'user_id', 'Ropproject_id'),
        Index('ix_user_project_access_user_du', 'user_id', 'DUproject_id'),
    )