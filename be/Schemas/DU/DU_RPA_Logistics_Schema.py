"""
DU RPA Logistics Schemas - Pydantic schemas for DU RPA Logistics section

Schemas for:
- Project: Create, Update, Out
- Description: Create, Update, Out (with calculated stats)
- Invoice: Create, Out
- InvoiceItem: Create, Out
- Various response models
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date


# ===========================
# PROJECT SCHEMAS
# ===========================

class CreateDURPAProject(BaseModel):
    """Schema for creating a new DU RPA Project."""
    po_number: str = Field(..., min_length=1, description="Unique PO#")


class UpdateDURPAProject(BaseModel):
    """Schema for updating an existing DU RPA Project."""
    po_number: Optional[str] = Field(None, min_length=1)


class DURPAProjectOut(BaseModel):
    """Schema for returning a DU RPA Project."""
    id: int
    po_number: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DURPAProjectWithStats(BaseModel):
    """Schema for returning a DU RPA Project with summary stats."""
    id: int
    po_number: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    description_count: int = 0
    invoice_count: int = 0
    total_po_value: float = 0
    total_billed_value: float = 0

    class Config:
        from_attributes = True


# ===========================
# DESCRIPTION SCHEMAS
# ===========================

class CreateDURPADescription(BaseModel):
    """Schema for creating a new DU RPA Description."""
    description: str = Field(..., min_length=1)
    po_line_item: Optional[str] = None
    po_qty_as_per_po: Optional[float] = None
    po_qty_per_unit: Optional[float] = None
    price_per_unit: Optional[float] = None


class UpdateDURPADescription(BaseModel):
    """Schema for updating an existing DU RPA Description."""
    description: Optional[str] = Field(None, min_length=1)
    po_line_item: Optional[str] = None
    po_qty_as_per_po: Optional[float] = None
    po_qty_per_unit: Optional[float] = None
    price_per_unit: Optional[float] = None


class DURPADescriptionOut(BaseModel):
    """Schema for returning a DU RPA Description (basic)."""
    id: int
    project_id: int
    description: str
    po_line_item: Optional[str] = None
    po_qty_as_per_po: Optional[float] = None
    po_qty_per_unit: Optional[float] = None
    price_per_unit: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DURPADescriptionWithStats(BaseModel):
    """
    Schema for returning a DU RPA Description with calculated stats.

    Calculated fields:
    - total_po_value: po_qty_per_unit * price_per_unit
    - actual_qty_billed: SUM of quantities from invoice items
    - actual_value_billed: actual_qty_billed * price_per_unit
    - balance: po_qty_per_unit - actual_qty_billed
    """
    id: int
    project_id: int
    description: str
    po_line_item: Optional[str] = None
    po_qty_as_per_po: Optional[float] = None
    po_qty_per_unit: Optional[float] = None
    price_per_unit: Optional[float] = None

    # Calculated Stats
    total_po_value: float = 0
    actual_qty_billed: float = 0
    actual_value_billed: float = 0
    balance: float = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===========================
# INVOICE SCHEMAS
# ===========================

class InvoiceItemInput(BaseModel):
    """Schema for invoice item input."""
    li_number: Optional[str] = None  # LI# - Line Item number
    description: str  # Description text to match
    quantity: float  # QTY
    unit_price: Optional[float] = None  # Unit price
    pac_date: Optional[date] = None  # PAC date


class CreateDURPAInvoice(BaseModel):
    """Schema for creating a new DU RPA Invoice."""
    ppo_number: str = Field(..., min_length=1, description="PPO# - unique per invoice")
    new_po_number: Optional[str] = None
    pr_number: Optional[str] = None
    site_id: Optional[str] = None
    model: Optional[str] = None
    sap_invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    customer_invoice_number: Optional[str] = None
    prf_percentage: Optional[float] = None
    vat_rate: Optional[float] = None
    items: List[InvoiceItemInput] = []


class DURPAInvoiceItemOut(BaseModel):
    """Schema for returning a DU RPA Invoice Item."""
    id: int
    invoice_id: int
    description_id: int
    li_number: Optional[str] = None  # LI# - Line Item number
    quantity: float  # QTY
    unit_price: Optional[float] = None  # Unit price
    pac_date: Optional[date] = None  # PAC date
    description_text: Optional[str] = None  # Joined from description table

    class Config:
        from_attributes = True


class DURPAInvoiceOut(BaseModel):
    """Schema for returning a DU RPA Invoice."""
    id: int
    project_id: int
    ppo_number: str  # PPO# - unique per invoice
    new_po_number: Optional[str] = None  # New PO number
    pr_number: Optional[str] = None  # PR #
    site_id: Optional[str] = None  # Site ID
    model: Optional[str] = None  # Model
    sap_invoice_number: Optional[str] = None  # SAP Invoice
    invoice_date: Optional[date] = None  # Invoice Date
    customer_invoice_number: Optional[str] = None  # Customer Invoice
    prf_percentage: Optional[float] = None  # PRF %
    vat_rate: Optional[float] = None  # VAT Rate
    created_at: Optional[datetime] = None
    items: List[DURPAInvoiceItemOut] = []

    class Config:
        from_attributes = True


# ===========================
# PAGINATION & RESPONSE SCHEMAS
# ===========================

class DURPAProjectPagination(BaseModel):
    """Schema for paginated DU RPA Project responses."""
    records: List[DURPAProjectWithStats]
    total: int

    class Config:
        from_attributes = True


class DURPADescriptionPagination(BaseModel):
    """Schema for paginated DU RPA Description responses."""
    records: List[DURPADescriptionWithStats]
    total: int

    class Config:
        from_attributes = True


class DURPAInvoicePagination(BaseModel):
    """Schema for paginated DU RPA Invoice responses."""
    records: List[DURPAInvoiceOut]
    total: int

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Schema for CSV upload response."""
    inserted: int
    errors: List[str] = []
    message: str


class BulkDescriptionUpload(BaseModel):
    """Schema for bulk description upload."""
    descriptions: List[CreateDURPADescription]
