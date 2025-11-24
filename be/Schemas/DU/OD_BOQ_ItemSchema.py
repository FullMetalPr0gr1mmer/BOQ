"""
OD BOQ Item Schema - Pydantic schemas for BOQ items with multi-level header structure

Schemas for:
- Create: Creating new BOQ items
- Update: Updating existing BOQ items
- Out: Response model for BOQ items
- Pagination: Paginated list response
- Stats: Statistics response
- Upload: CSV upload response
- CategorySum: Sum by category response
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CreateODBOQItem(BaseModel):
    """Schema for creating a new BOQ item."""

    # Fixed metadata columns
    cat: Optional[str] = None
    bu: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    uom: Optional[str] = None

    # Scope quantity columns
    new_sran: Optional[float] = Field(None, description="New SRAN quantity")
    sran_exp_1cc_l800: Optional[float] = Field(None, description="SRAN Expansion 1cc to 3cc (L800)")
    sran_exp_1cc_l1800: Optional[float] = Field(None, description="SRAN Expansion 1cc to 3cc (L1800)")
    sran_exp_2cc_l800_l1800: Optional[float] = Field(None, description="SRAN Expansion 2cc to 3cc (L800+L1800)")
    sran_exp_2cc_l1800_l2100: Optional[float] = Field(None, description="SRAN Expansion 2cc to 3cc (L1800+L2100)")
    sran_exp_2cc_l800_l2100: Optional[float] = Field(None, description="SRAN Expansion 2cc to 3cc (L800+L2100)")
    new_5g_n78: Optional[float] = Field(None, description="New 5G-n78 quantity")
    exp_5g_3cc: Optional[float] = Field(None, description="5G Expansion-3CC quantity")
    exp_5g_n41_reuse: Optional[float] = Field(None, description="5G Expansion-n41 Re-use quantity")
    exp_5g_3cc_ontop: Optional[float] = Field(None, description="5G Expansion-3CC ontop existing n41")
    exp_5g_band_swap: Optional[float] = Field(None, description="5G Expansion-Band Swap quantity")
    nr_fdd_model1_activation: Optional[float] = Field(None, description="5G-NR FDD-Model 1 activation")
    nr_fdd_model1_tdra: Optional[float] = Field(None, description="5G-NR FDD-Model 1 TDRA Scope")
    nr_fdd_model1_2025: Optional[float] = Field(None, description="5G-NR FDD-Model 1 2025 Scope")
    antenna_cutover_ipaa: Optional[float] = Field(None, description="Antenna Cutover (IPAA+)")
    total_qty: Optional[float] = Field(None, description="Total quantity")

    # Foreign key
    project_id: Optional[str] = None


class UpdateODBOQItem(BaseModel):
    """Schema for updating an existing BOQ item."""

    # Fixed metadata columns
    cat: Optional[str] = None
    bu: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    uom: Optional[str] = None

    # Scope quantity columns
    new_sran: Optional[float] = None
    sran_exp_1cc_l800: Optional[float] = None
    sran_exp_1cc_l1800: Optional[float] = None
    sran_exp_2cc_l800_l1800: Optional[float] = None
    sran_exp_2cc_l1800_l2100: Optional[float] = None
    sran_exp_2cc_l800_l2100: Optional[float] = None
    new_5g_n78: Optional[float] = None
    exp_5g_3cc: Optional[float] = None
    exp_5g_n41_reuse: Optional[float] = None
    exp_5g_3cc_ontop: Optional[float] = None
    exp_5g_band_swap: Optional[float] = None
    nr_fdd_model1_activation: Optional[float] = None
    nr_fdd_model1_tdra: Optional[float] = None
    nr_fdd_model1_2025: Optional[float] = None
    antenna_cutover_ipaa: Optional[float] = None
    total_qty: Optional[float] = None

    # Foreign key
    project_id: Optional[str] = None


class ODBOQItemOut(BaseModel):
    """Schema for returning a BOQ item."""

    id: int

    # Fixed metadata columns
    cat: Optional[str] = None
    bu: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    uom: Optional[str] = None

    # Scope quantity columns
    new_sran: Optional[float] = None
    sran_exp_1cc_l800: Optional[float] = None
    sran_exp_1cc_l1800: Optional[float] = None
    sran_exp_2cc_l800_l1800: Optional[float] = None
    sran_exp_2cc_l1800_l2100: Optional[float] = None
    sran_exp_2cc_l800_l2100: Optional[float] = None
    new_5g_n78: Optional[float] = None
    exp_5g_3cc: Optional[float] = None
    exp_5g_n41_reuse: Optional[float] = None
    exp_5g_3cc_ontop: Optional[float] = None
    exp_5g_band_swap: Optional[float] = None
    nr_fdd_model1_activation: Optional[float] = None
    nr_fdd_model1_tdra: Optional[float] = None
    nr_fdd_model1_2025: Optional[float] = None
    antenna_cutover_ipaa: Optional[float] = None
    total_qty: Optional[float] = None

    # Foreign key
    project_id: Optional[str] = None

    class Config:
        from_attributes = True


class ODBOQItemPagination(BaseModel):
    """Schema for paginated BOQ item responses."""
    records: List[ODBOQItemOut]
    total: int

    class Config:
        from_attributes = True


class ODBOQItemStatsResponse(BaseModel):
    """Schema for BOQ item statistics."""
    total_items: int
    unique_categories: int
    unique_bus: int
    total_new_sran: Optional[float] = None
    total_5g: Optional[float] = None
    total_services: Optional[float] = None


class UploadResponse(BaseModel):
    """Schema for CSV upload response."""
    inserted: int
    updated: int
    skipped: int
    message: str


class CategorySumResponse(BaseModel):
    """Schema for sum by category response."""
    category: str
    level1_header: str
    total: float
    non_zero_count: int


class Level1CategorySummary(BaseModel):
    """Schema for Level 1 category summary."""
    category: str
    total_quantity: float
    column_count: int


class ColumnHeaderInfo(BaseModel):
    """Schema for column header information."""
    field_name: str
    level1_header: str
    level2_header: str
    column_index: int


class FilterOptions(BaseModel):
    """Schema for filter options response."""
    cats: List[str]
    bus: List[str]
    categories: List[str]
    uoms: List[str]
    projects: List[str]


class BulkUpdateRequest(BaseModel):
    """Schema for bulk update request."""
    item_ids: List[int]
    updates: Dict[str, Any]


class CompareCategories(BaseModel):
    """Schema for category comparison request."""
    category1: str
    category2: str
    operation: str = "difference"  # "difference", "ratio", "sum"


class CompareCategoriesResponse(BaseModel):
    """Schema for category comparison response."""
    cat: Optional[str] = None
    description: Optional[str] = None
    category1_total: float
    category2_total: float
    result: Optional[float] = None
