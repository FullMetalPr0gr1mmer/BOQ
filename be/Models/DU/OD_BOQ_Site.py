"""
OD BOQ Site Model - Parent table for site/project information

This model represents individual sites/projects in the BOQ tracking system.
Each site has multiple products with quantities tracked in the OD_BOQ_Site_Product junction table.
"""

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Integer
from Database.session import Base


class ODBOQSite(Base):
    """Site/Project information for BOQ tracking"""
    __tablename__ = 'du_od_boq_site'

    # Primary key (auto-increment ID since site_id can be duplicated with different subscopes)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Site identifier (can be duplicated with different subscopes)
    site_id = Column(String(100), nullable=False, index=True)  # e.g., "AUH8976"

    # Site metadata
    region = Column(String(100), nullable=True)
    distance = Column(String(100), nullable=True)
    scope = Column(String(100), index=True, nullable=True)  # e.g., "5G", "SRAN"
    subscope = Column(String(200), index=True, nullable=True)  # e.g., "New 5G-n78", "Bandswap"
    po_model = Column(String(500), nullable=True)  # PO model string

    # Foreign key to DU Project
    project_id = Column(String(200), ForeignKey("du_project.pid_po"), index=True, nullable=True)

    # Additional site metadata (from CSV columns after products)
    ac_armod_cable = Column(String(100), nullable=True)  # AC ARMOD Cable
    additional_cost = Column(String(100), nullable=True)  # Additional Cost - 4x4
    remark = Column(String(500), nullable=True)  # Any Remark
    partner = Column(String(200), nullable=True, index=True)  # Partner
    request_status = Column(String(100), nullable=True, index=True)  # Request Status
    requested_date = Column(String(100), nullable=True)  # Requested Date
    du_po_number = Column(String(100), nullable=True, index=True)  # Du PO#
    smp = Column(String(100), nullable=True)  # SMP
    year_scope = Column(String(50), nullable=True)  # Year Scope
    integration_status = Column(String(100), nullable=True, index=True)  # Integration Status
    integration_date = Column(String(100), nullable=True)  # Integration Date
    du_po_convention_name = Column(String(200), nullable=True)  # Du PO Convention name
    po_year_issuance = Column(String(50), nullable=True)  # PO Year Issuance

    # Unique constraint: same site_id can exist but not with same subscope
    __table_args__ = (
        UniqueConstraint('site_id', 'subscope', name='uix_site_subscope'),
    )

    # Note: Site products are stored in OD_BOQ_Site_Product junction table
