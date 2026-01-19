"""
OD BOQ Product Model - Product master catalog

This model stores the product catalog with metadata.
Each product can be associated with multiple sites via the OD_BOQ_Site_Product junction table.
"""

from sqlalchemy import Column, Integer, String, Float
from Database.session import Base


class ODBOQProduct(Base):
    """Product catalog for BOQ items"""
    __tablename__ = 'du_od_boq_product'

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Product metadata (from CSV header rows 1-7)
    description = Column(String(500), nullable=True, index=True)  # Row 1: Product description
    line_number = Column(String(50), nullable=True)  # Row 2: #Line
    code = Column(String(50), nullable=True, index=True)  # Row 3: #Code
    category = Column(String(100), nullable=True, index=True)  # Row 4: Hardware/SW/Service
    bu = Column(String(100), nullable=True, index=True)  # Business Unit (e.g., "Product", "Services")

    # Inventory tracking
    total_po_qty = Column(Float, nullable=True)  # Row 5: Total PO QTY
    consumed_in_year = Column(Float, nullable=True)  # Row 6: Consumed quantity
    consumed_year = Column(Integer, nullable=True)  # Year of consumption (e.g., 2026)
    remaining_in_po = Column(Float, nullable=True)  # Row 7: Remaining in PO

    # Note: Site-product quantities are stored in OD_BOQ_Site_Product junction table
