"""
DU RPA Logistics Models - SQLAlchemy models for DU RPA Logistics section

Models:
- DURPAProject: Main project entity with unique PO#
- DURPADescription: Line items/descriptions for each project (Stats)
- DURPAInvoice: Invoice headers uploaded via CSV
- DURPAInvoiceItem: Individual invoice line items with quantities
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from Database.session import Base


class DURPAProject(Base):
    """DU RPA Logistics Project - identified by unique PO#"""
    __tablename__ = 'du_rpa_project'

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    descriptions = relationship("DURPADescription", back_populates="project", cascade="all, delete-orphan")
    invoices = relationship("DURPAInvoice", back_populates="project", cascade="all, delete-orphan")


class DURPADescription(Base):
    """
    DU RPA Description - Line items for a project (Stats)

    User Input Fields:
    - description: The description text
    - po_line_item: PO Line Item identifier
    - po_qty_as_per_po: PO Qty (as per PO)
    - po_qty_per_unit: PO Qty (per unit)
    - price_per_unit: Price per Unit

    Calculated Fields (computed via API):
    - total_po_value: po_qty_per_unit * price_per_unit
    - actual_qty_billed: SUM of quantities from invoice items
    - actual_value_billed: actual_qty_billed * price_per_unit
    - balance: po_qty_per_unit - actual_qty_billed
    """
    __tablename__ = 'du_rpa_description'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('du_rpa_project.id', ondelete='CASCADE'), nullable=False, index=True)

    # Description text
    description = Column(Text, nullable=False)

    # User Input Stats
    po_line_item = Column(String(100), nullable=True)
    po_qty_as_per_po = Column(Float, nullable=True)
    po_qty_per_unit = Column(Float, nullable=True)
    price_per_unit = Column(Float, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("DURPAProject", back_populates="descriptions")
    invoice_items = relationship("DURPAInvoiceItem", back_populates="description")


class DURPAInvoice(Base):
    """
    DU RPA Invoice - Invoice header uploaded via CSV

    Fields:
    - ppo_number: PPO# (unique per invoice, prevents duplicates)
    - new_po_number: New PO number
    - pr_number: PR #
    - site_id: Site ID
    - model: Model
    - sap_invoice_number: SAP Invoice #
    - invoice_date: Invoice Date
    - customer_invoice_number: Customer Invoice #
    """
    __tablename__ = 'du_rpa_invoice'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('du_rpa_project.id', ondelete='CASCADE'), nullable=False, index=True)

    # Invoice fields
    ppo_number = Column(String(100), unique=True, nullable=False, index=True)  # PPO# - unique identifier
    new_po_number = Column(String(100), nullable=True, index=True)  # New PO number
    pr_number = Column(String(100), nullable=True, index=True)  # PR #
    site_id = Column(String(100), nullable=True, index=True)
    model = Column(String(200), nullable=True)  # Model
    sap_invoice_number = Column(String(100), nullable=True, index=True)
    invoice_date = Column(Date, nullable=True)
    customer_invoice_number = Column(String(100), nullable=True, index=True)
    prf_percentage = Column(Float, nullable=True)  # PRF %
    vat_rate = Column(Float, nullable=True)  # VAT Rate

    created_at = Column(DateTime, default=func.now())

    # Relationships
    project = relationship("DURPAProject", back_populates="invoices")
    items = relationship("DURPAInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class DURPAInvoiceItem(Base):
    """
    DU RPA Invoice Item - Individual line item within an invoice

    Fields:
    - li_number: LI# (Line Item number)
    - description_id: Links to the description
    - quantity: QTY
    - unit_price: Unit price (validated against description's price_per_unit)
    - pac_date: PAC date
    """
    __tablename__ = 'du_rpa_invoice_item'

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('du_rpa_invoice.id', ondelete='CASCADE'), nullable=False, index=True)
    description_id = Column(Integer, ForeignKey('du_rpa_description.id', ondelete='NO ACTION'), nullable=False, index=True)

    # Invoice item fields
    li_number = Column(String(100), nullable=True, index=True)  # LI# - Line Item number
    quantity = Column(Float, nullable=False, default=0)  # QTY
    unit_price = Column(Float, nullable=True)  # Unit price
    pac_date = Column(Date, nullable=True)  # PAC date

    created_at = Column(DateTime, default=func.now())

    # Relationships
    invoice = relationship("DURPAInvoice", back_populates="items")
    description = relationship("DURPADescription", back_populates="invoice_items")
