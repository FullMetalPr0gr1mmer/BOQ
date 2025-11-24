"""
Customer PO Model - SQLAlchemy model for Customer Purchase Order items

This model represents the Customer PO items with:
- Line number and category information
- Item/Job codes and descriptions
- Quantity, UOM, Price, Amount
- Status tracking
- Reference to DU Project

The CSV has a header structure:
- Rows 1-2: Header info (Supplier, Order Date, etc.) - ignored
- Row 5: Column headers
- Row 6+: Data rows
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from Database.session import Base


class CustomerPO(Base):
    """Customer Purchase Order item model"""
    __tablename__ = 'du_customer_po'

    id = Column(Integer, primary_key=True, index=True)

    # Line number
    line = Column(Integer, nullable=True, index=True)

    # Category (e.g., "OD", "IBS")
    cat = Column(String(50), index=True, nullable=True)

    # Item/Job code (e.g., "467831A.101")
    item_job = Column(String(100), index=True, nullable=True)

    # PCI (e.g., "1")
    pci = Column(String(50), nullable=True)

    # SI (e.g., "1.1")
    si = Column(String(50), nullable=True)

    # Supplier Item
    supplier_item = Column(String(200), nullable=True)

    # Description (main product description)
    description = Column(Text, nullable=True)

    # Quantity
    quantity = Column(Float, nullable=True)

    # Unit of Measure (e.g., "each", "per site")
    uom = Column(String(50), nullable=True)

    # Price (unit price)
    price = Column(Float, nullable=True)

    # Amount (quantity * price)
    amount = Column(Float, nullable=True)

    # Status (e.g., "Active", "Pending")
    status = Column(String(100), nullable=True)

    # Foreign key to DU Project
    project_id = Column(String(200), ForeignKey("du_project.pid_po"), index=True, nullable=True)


# Column mapping for CSV import
# Maps column index to model field name (based on row 5 headers)
# Note: Column 5 is a duplicate "Item/Job" header (empty in data) - we skip it
CSV_COLUMN_MAPPING = {
    0: 'line',           # Line
    1: 'cat',            # CAT
    2: 'item_job',       # Item/Job (first one - the item code)
    3: 'pci',            # PCI
    4: 'si',             # SI
    # 5: skipped         # Item/Job (duplicate - usually empty)
    6: 'supplier_item',  # Supplier Item
    7: 'description',    # Description
    8: 'quantity',       # Quantity
    9: 'uom',            # UOM
    10: 'price',         # Price
    11: 'amount',        # Amount
    12: 'status',        # Status
}

# Reverse mapping (field name to column index)
FIELD_TO_COLUMN = {v: k for k, v in CSV_COLUMN_MAPPING.items()}

# Column headers for display
COLUMN_HEADERS = {
    'line': 'Line',
    'cat': 'CAT',
    'item_job': 'Item/Job',
    'pci': 'PCI',
    'si': 'SI',
    'supplier_item': 'Supplier Item',
    'description': 'Description',
    'quantity': 'Quantity',
    'uom': 'UOM',
    'price': 'Price',
    'amount': 'Amount',
    'status': 'Status',
}

# Numeric fields that need type conversion
NUMERIC_FIELDS = ['line', 'quantity', 'price', 'amount']

# String fields
STRING_FIELDS = ['cat', 'item_job', 'pci', 'si', 'supplier_item', 'description', 'uom', 'status']
