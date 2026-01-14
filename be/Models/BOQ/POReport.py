from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
import uuid
from Database.session import Base


class POReport(Base):
    __tablename__ = "po_report"

    id = Column(String(200), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))

    # CSV Columns
    pur_doc = Column(String(200), nullable=True, index=True)  # Pur. Doc.
    customer_site_ref = Column(String(200), nullable=True, index=True)  # Customer Site Ref
    project = Column(String(200), nullable=True)  # Project
    so_number = Column(String(200), nullable=True)  # SO#
    material_des = Column(Text, nullable=True)  # Material DES
    rr_date = Column(String(100), nullable=True)  # RR Date
    site_name = Column(String(500), nullable=True)  # Site name
    wbs_element = Column(String(200), nullable=True)  # WBS Element
    supplier = Column(String(200), nullable=True)  # Supplier
    name_1 = Column(String(500), nullable=True)  # Name 1
    order_date = Column(String(100), nullable=True)  # Order date
    gr_date = Column(String(100), nullable=True)  # GR date
    supplier_invoice = Column(String(200), nullable=True)  # Supplier Invoice
    ir_docdate = Column(String(100), nullable=True)  # IR Docdate
    pstng_date = Column(String(100), nullable=True)  # Pstng Date
    po_value_sar = Column(String(200), nullable=True)  # PO Value SAR
    invoiced_value_sar = Column(String(200), nullable=True)  # Invoiced Value SAR
    percent_invoiced = Column(String(50), nullable=True)  # % Invoiced
    balance_value_sar = Column(String(200), nullable=True)  # Balance Value SAR
    svo_number = Column(String(200), nullable=True)  # SVO Number
    header_text = Column(Text, nullable=True)  # Header text
    smp_id = Column(String(200), nullable=True)  # SMP ID
    remarks = Column(Text, nullable=True)  # Remarks
    aind = Column(String(100), nullable=True)  # AInd
    accounting_indicator_desc = Column(Text, nullable=True)  # Accounting indicator desc

    # Metadata columns
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
