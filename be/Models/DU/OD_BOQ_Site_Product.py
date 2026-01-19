"""
OD BOQ Site Product Model - Junction table for site-product quantities

This model represents the many-to-many relationship between sites and products,
storing the quantity of each product for each site.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from Database.session import Base


class ODBOQSiteProduct(Base):
    """Site-Product junction table with quantities"""
    __tablename__ = 'du_od_boq_site_product'

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign keys
    site_id = Column(String(100), ForeignKey("du_od_boq_site.site_id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("du_od_boq_product.id"), nullable=False, index=True)

    # Quantity for this site-product combination
    qty_per_site = Column(Float, nullable=True)

    # Unique constraint to prevent duplicate site-product combinations
    __table_args__ = (
        UniqueConstraint('site_id', 'product_id', name='uix_site_product'),
    )
