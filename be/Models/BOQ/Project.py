"""
BOQ Project Model

This module defines the Project model for the Bill of Quantities (BOQ) system.
A Project represents a telecommunications infrastructure project with unique
identifiers and basic project information.

Database Table: projects

The Project model serves as a foundation for organizing BOQ data and is referenced
by other models throughout the system for project-specific operations.

Author: [Your Name]
Created: [Date]
Last Modified: [Date]
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from Database.session import Base


class Project(Base):
    """
    Project Model - Represents a telecommunications infrastructure project.

    This model stores basic project information including project identifiers,
    purchase order details, and project names. It serves as the primary reference
    for organizing all BOQ-related data within the system.

    Attributes:
        pid_po (str): Primary key - Combined Project ID and Purchase Order identifier
                      Format: Usually combines PID and PO with a separator
                      Max length: 200 characters
                      Example: "PRJ001_PO123"

        pid (str): Project ID - Unique identifier for the project
                   Max length: 100 characters
                   Example: "PRJ001"

        po (str): Purchase Order number - Financial tracking identifier
                  Max length: 100 characters
                  Example: "PO123"

        project_name (str): Human-readable project name/description
                           Max length: 200 characters
                           Example: "Metro Network Expansion Phase 1"

    Indexes:
        - Primary key index on pid_po
        - Index on pid for fast project lookups
        - Index on po for purchase order tracking
        - Index on project_name for search functionality

    Relationships:
        This model is referenced by various other models including:
        - Inventory items
        - BOQ levels and structures
        - LLD (Low Level Design) items
        - Dismantling records

    Usage Example:
        project = Project(
            pid_po="PRJ001_PO123",
            pid="PRJ001",
            po="PO123",
            project_name="Metro Network Expansion Phase 1"
        )
    """
    __tablename__ = 'projects'

    # Primary key: Combined project and purchase order identifier
    pid_po = Column(String(200), primary_key=True, index=True)

    # Project identifier
    pid = Column(String(100), index=True)

    # Purchase order number
    po = Column(String(100), index=True)

    # Project name/description
    project_name = Column(String(200), index=True)


