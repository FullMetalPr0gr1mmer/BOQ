"""
Price Book Model
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from Database.session import Base


class PriceBook(Base):
    __tablename__ = 'price_books'
    __table_args__ = (
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)

    # Price Book columns based on actual CSV headers
    project_name = Column(String(500), nullable=True)  # Project Name
    merge_poline_uplline = Column(String(200), nullable=True)  # Merge POLine#UPLLine#
    po_number = Column(String(200), nullable=True, index=True)  # PO#
    customer_item_type = Column(String(200), nullable=True)  # *Customer Item Type
    local_content = Column(String(200), nullable=True)  # Local Content
    scope = Column(Text, nullable=True)  # Scope
    sub_scope = Column(Text, nullable=True)  # Sub Scope
    po_line = Column(String(200), nullable=True)  # PO line
    upl_line = Column(String(200), nullable=True)  # UPL Line
    merge_po_poline_uplline = Column(String(200), nullable=True)  # Merge PO#, POLine#, UPLLine#
    vendor_part_number_item_code = Column(String(500), nullable=True)  # Vendor Part Number (Item Code)
    po_line_item_description = Column(Text, nullable=True)  # PO Line Item Description
    zain_item_category = Column(Text, nullable=True)  # Zain Item Category (Reference Categories Sheet)
    serialized = Column(String(100), nullable=True)  # Serialized (when delivered will have serial no)
    active_or_passive = Column(String(100), nullable=True)  # Active or Passive
    uom = Column(String(100), nullable=True)  # UOM
    quantity = Column(String(200), nullable=True)  # *Quantity
    unit = Column(String(100), nullable=True)  # Unit
    currency = Column(String(50), nullable=True)  # *Currency
    discount = Column(String(200), nullable=True)  # Discount
    unit_price_before_discount = Column(String(200), nullable=True)  # *Unit Price before discount
    po_total_amt_before_discount = Column(String(200), nullable=True)  # PO Total amt before discount
    special_discount = Column(Text, nullable=True)  # Special Discount given for this project only
    claimed_percentage_after_special_discount = Column(Text, nullable=True)  # Claimed percentage after Special Discount
    unit_price_sar_after_special_discount = Column(String(200), nullable=True)  # Unit Price(SAR) after Special Discount
    old_up = Column(String(200), nullable=True)  # old UP
    delta = Column(String(200), nullable=True)  # Delta
    final_total_price_after_discount = Column(String(200), nullable=True)  # Final Total Price After Discount
    fv_percent_as_per_rrb = Column(String(200), nullable=True)  # FV % as per RRB
    fv = Column(String(200), nullable=True)  # FV
    total_fv_sar = Column(String(200), nullable=True)  # Total FV SAR
    revised_fv_percent = Column(String(200), nullable=True)  # Revised FV%
    fv_unit_price_after_descope = Column(String(200), nullable=True)  # FV Unit Price after Descope
    to_go_contract_price_eur = Column(String(200), nullable=True)  # To Go Contract Price Eur
    r_ssp_eur = Column(String(200), nullable=True)  # R SSP Eur

    # Metadata
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    uploader = relationship("User", foreign_keys=[uploaded_by])
