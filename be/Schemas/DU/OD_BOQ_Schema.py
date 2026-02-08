"""
OD BOQ Schemas - Pydantic schemas for the new 3-table structure

Tables:
1. OD_BOQ_Site: Site/project information
2. OD_BOQ_Product: Product catalog
3. OD_BOQ_Site_Product: Junction table with quantities

Schemas for CRUD operations, pagination, stats, and CSV upload.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ===========================
# SITE SCHEMAS
# ===========================

class ODBOQSiteCreate(BaseModel):
    """Schema for creating a new site."""
    site_id: str = Field(..., description="Site identifier (can be duplicated with different subscopes)")
    region: Optional[str] = None
    distance: Optional[str] = None
    scope: Optional[str] = Field(None, description="5G, SRAN, etc.")
    subscope: Optional[str] = Field(None, description="New 5G-n78, Bandswap, etc.")
    po_model: Optional[str] = Field(None, description="PO model string")
    project_id: Optional[str] = None
    # Additional metadata
    ac_armod_cable: Optional[str] = None
    additional_cost: Optional[str] = None
    remark: Optional[str] = None
    partner: Optional[str] = None
    request_status: Optional[str] = None
    requested_date: Optional[str] = None
    du_po_number: Optional[str] = None
    smp: Optional[str] = None
    year_scope: Optional[str] = None
    integration_status: Optional[str] = None
    integration_date: Optional[str] = None
    du_po_convention_name: Optional[str] = None
    po_year_issuance: Optional[str] = None


class ODBOQSiteUpdate(BaseModel):
    """Schema for updating a site."""
    region: Optional[str] = None
    distance: Optional[str] = None
    scope: Optional[str] = None
    subscope: Optional[str] = None
    po_model: Optional[str] = None
    project_id: Optional[str] = None
    # Additional metadata
    ac_armod_cable: Optional[str] = None
    additional_cost: Optional[str] = None
    remark: Optional[str] = None
    partner: Optional[str] = None
    request_status: Optional[str] = None
    requested_date: Optional[str] = None
    du_po_number: Optional[str] = None
    smp: Optional[str] = None
    year_scope: Optional[str] = None
    integration_status: Optional[str] = None
    integration_date: Optional[str] = None
    du_po_convention_name: Optional[str] = None
    po_year_issuance: Optional[str] = None


class ODBOQSiteOut(BaseModel):
    """Schema for returning a site."""
    id: int
    site_id: str
    region: Optional[str] = None
    distance: Optional[str] = None
    scope: Optional[str] = None
    subscope: Optional[str] = None
    po_model: Optional[str] = None
    project_id: Optional[str] = None
    # Additional metadata
    ac_armod_cable: Optional[str] = None
    additional_cost: Optional[str] = None
    remark: Optional[str] = None
    partner: Optional[str] = None
    request_status: Optional[str] = None
    requested_date: Optional[str] = None
    du_po_number: Optional[str] = None
    smp: Optional[str] = None
    year_scope: Optional[str] = None
    integration_status: Optional[str] = None
    integration_date: Optional[str] = None
    du_po_convention_name: Optional[str] = None
    po_year_issuance: Optional[str] = None

    class Config:
        from_attributes = True


# ===========================
# PRODUCT SCHEMAS
# ===========================

class ODBOQProductCreate(BaseModel):
    """Schema for creating a new product."""
    description: Optional[str] = Field(None, description="Product description")
    line_number: Optional[str] = Field(None, description="#Line from CSV")
    code: Optional[str] = Field(None, description="#Code from CSV")
    category: Optional[str] = Field(None, description="Hardware/SW/Service")
    bu: Optional[str] = Field(None, description="Business Unit (Product, Services, etc.)")
    total_po_qty: Optional[float] = Field(None, description="Total PO quantity")
    consumed_in_year: Optional[float] = Field(None, description="Consumed quantity")
    consumed_year: Optional[int] = Field(None, description="Year of consumption")
    remaining_in_po: Optional[float] = Field(None, description="Remaining quantity")


class ODBOQProductUpdate(BaseModel):
    """Schema for updating a product."""
    description: Optional[str] = None
    line_number: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    bu: Optional[str] = None
    total_po_qty: Optional[float] = None
    consumed_in_year: Optional[float] = None
    consumed_year: Optional[int] = None
    remaining_in_po: Optional[float] = None


class ODBOQProductOut(BaseModel):
    """Schema for returning a product."""
    id: int
    description: Optional[str] = None
    line_number: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    bu: Optional[str] = None
    total_po_qty: Optional[float] = None
    consumed_in_year: Optional[float] = None
    consumed_year: Optional[int] = None
    remaining_in_po: Optional[float] = None

    class Config:
        from_attributes = True


# ===========================
# SITE-PRODUCT JUNCTION SCHEMAS
# ===========================

class ODBOQSiteProductCreate(BaseModel):
    """Schema for creating a site-product quantity."""
    site_record_id: int
    product_id: int
    qty_per_site: Optional[float] = Field(None, description="Quantity for this site-product combo")


class ODBOQSiteProductUpdate(BaseModel):
    """Schema for updating a site-product quantity."""
    qty_per_site: Optional[float] = None


class ODBOQSiteProductOut(BaseModel):
    """Schema for returning a site-product quantity."""
    id: int
    site_record_id: int
    product_id: int
    qty_per_site: Optional[float] = None

    class Config:
        from_attributes = True


# ===========================
# COMBINED/ENRICHED SCHEMAS
# ===========================

class SiteWithProductsOut(BaseModel):
    """Schema for returning a site with its products."""
    id: int
    site_id: str
    region: Optional[str] = None
    distance: Optional[str] = None
    scope: Optional[str] = None
    subscope: Optional[str] = None
    po_model: Optional[str] = None
    project_id: Optional[str] = None
    # Additional metadata
    ac_armod_cable: Optional[str] = None
    additional_cost: Optional[str] = None
    remark: Optional[str] = None
    partner: Optional[str] = None
    request_status: Optional[str] = None
    requested_date: Optional[str] = None
    du_po_number: Optional[str] = None
    smp: Optional[str] = None
    year_scope: Optional[str] = None
    integration_status: Optional[str] = None
    integration_date: Optional[str] = None
    du_po_convention_name: Optional[str] = None
    po_year_issuance: Optional[str] = None
    products: List[Dict[str, Any]] = Field(default_factory=list, description="Product details with quantities")
    total_qty_sum: Optional[float] = Field(None, description="Sum of all product quantities for this site")

    class Config:
        from_attributes = True


class ProductWithQuantity(BaseModel):
    """Product details with quantity for a specific site."""
    product_id: int
    description: Optional[str] = None
    line_number: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    qty_per_site: Optional[float] = None


# ===========================
# PAGINATION SCHEMAS
# ===========================

class ODBOQSitePagination(BaseModel):
    """Pagination response for sites."""
    records: List[ODBOQSiteOut]
    total: int


class ODBOQProductPagination(BaseModel):
    """Pagination response for products."""
    records: List[ODBOQProductOut]
    total: int


# ===========================
# STATISTICS & ANALYTICS
# ===========================

class ODBOQStatsResponse(BaseModel):
    """Statistics response."""
    total_sites: int = 0
    total_products: int = 0
    total_site_products: int = 0
    unique_scopes: int = 0
    unique_subscopes: int = 0
    unique_categories: int = 0


class FilterOptions(BaseModel):
    """Available filter options."""
    regions: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    subscopes: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)


# ===========================
# CSV UPLOAD SCHEMAS
# ===========================

class UploadResponse(BaseModel):
    """Response for CSV upload operations."""
    sites_inserted: int = 0
    sites_updated: int = 0
    products_inserted: int = 0
    products_updated: int = 0
    site_products_inserted: int = 0
    site_products_updated: int = 0
    skipped: int = 0
    message: str


# ===========================
# BULK OPERATION SCHEMAS
# ===========================

class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operations."""
    message: str
    deleted_sites: int = 0
    deleted_site_products: int = 0
