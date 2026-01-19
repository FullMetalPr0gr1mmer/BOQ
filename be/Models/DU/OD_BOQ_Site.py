"""
OD BOQ Site Model - Parent table for site/project information

This model represents individual sites/projects in the BOQ tracking system.
Each site has multiple products with quantities tracked in the OD_BOQ_Site_Product junction table.
"""

from sqlalchemy import Column, String, ForeignKey
from Database.session import Base


class ODBOQSite(Base):
    """Site/Project information for BOQ tracking"""
    __tablename__ = 'du_od_boq_site'

    # Primary key
    site_id = Column(String(100), primary_key=True, index=True)  # e.g., "AUH8976"

    # Site metadata
    region = Column(String(100), nullable=True)
    distance = Column(String(100), nullable=True)
    scope = Column(String(100), index=True, nullable=True)  # e.g., "5G", "SRAN"
    subscope = Column(String(200), index=True, nullable=True)  # e.g., "New 5G-n78", "Bandswap"
    po_model = Column(String(500), nullable=True)  # PO model string

    # Foreign key to DU Project
    project_id = Column(String(200), ForeignKey("du_project.pid_po"), index=True, nullable=True)

    # Note: Site products are stored in OD_BOQ_Site_Product junction table
