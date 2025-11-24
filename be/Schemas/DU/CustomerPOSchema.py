"""
Customer PO Schema - Pydantic schemas for Customer Purchase Order items

Schemas for:
- Create: Creating new Customer PO items
- Update: Updating existing Customer PO items
- Out: Response model for Customer PO items
- Pagination: Paginated list response
- Stats: Statistics response
- Upload: CSV upload response
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CreateCustomerPO(BaseModel):
    """Schema for creating a new Customer PO item."""

    # Line number
    line: Optional[int] = None

    # Fixed metadata columns
    cat: Optional[str] = None
    item_job: Optional[str] = None
    pci: Optional[str] = None
    si: Optional[str] = None
    supplier_item: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    uom: Optional[str] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    status: Optional[str] = None

    # Foreign key
    project_id: Optional[str] = None


class UpdateCustomerPO(BaseModel):
    """Schema for updating an existing Customer PO item."""

    # Line number
    line: Optional[int] = None

    # Fixed metadata columns
    cat: Optional[str] = None
    item_job: Optional[str] = None
    pci: Optional[str] = None
    si: Optional[str] = None
    supplier_item: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    uom: Optional[str] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    status: Optional[str] = None

    # Foreign key
    project_id: Optional[str] = None


class CustomerPOOut(BaseModel):
    """Schema for returning a Customer PO item."""

    id: int

    # Line number
    line: Optional[int] = None

    # Fixed metadata columns
    cat: Optional[str] = None
    item_job: Optional[str] = None
    pci: Optional[str] = None
    si: Optional[str] = None
    supplier_item: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    uom: Optional[str] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    status: Optional[str] = None

    # Foreign key
    project_id: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerPOPagination(BaseModel):
    """Schema for paginated Customer PO item responses."""
    records: List[CustomerPOOut]
    total: int

    class Config:
        from_attributes = True


class CustomerPOStatsResponse(BaseModel):
    """Schema for Customer PO item statistics."""
    total_items: int
    unique_categories: int
    total_quantity: Optional[float] = None
    total_amount: Optional[float] = None
    unique_statuses: int


class UploadResponse(BaseModel):
    """Schema for CSV upload response."""
    inserted: int
    updated: int
    skipped: int
    message: str


class FilterOptions(BaseModel):
    """Schema for filter options response."""
    cats: List[str]
    statuses: List[str]
    uoms: List[str]
    projects: List[str]


class ColumnHeaderInfo(BaseModel):
    """Schema for column header information."""
    field_name: str
    header: str
    column_index: int


class BulkUpdateRequest(BaseModel):
    """Schema for bulk update request."""
    item_ids: List[int]
    updates: Dict[str, Any]


class CategorySummary(BaseModel):
    """Schema for category summary."""
    category: str
    item_count: int
    total_quantity: Optional[float] = None
    total_amount: Optional[float] = None
