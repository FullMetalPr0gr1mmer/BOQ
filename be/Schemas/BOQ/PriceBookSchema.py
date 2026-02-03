from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PriceBookCreate(BaseModel):
    project_name: Optional[str] = None
    merge_poline_uplline: Optional[str] = None
    po_number: Optional[str] = None
    customer_item_type: Optional[str] = None
    local_content: Optional[str] = None
    scope: Optional[str] = None
    sub_scope: Optional[str] = None
    po_line: Optional[str] = None
    upl_line: Optional[str] = None
    merge_po_poline_uplline: Optional[str] = None
    vendor_part_number_item_code: Optional[str] = None
    po_line_item_description: Optional[str] = None
    zain_item_category: Optional[str] = None
    serialized: Optional[str] = None
    active_or_passive: Optional[str] = None
    uom: Optional[str] = None
    quantity: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    discount: Optional[str] = None
    unit_price_before_discount: Optional[str] = None
    po_total_amt_before_discount: Optional[str] = None
    special_discount: Optional[str] = None
    claimed_percentage_after_special_discount: Optional[str] = None
    unit_price_sar_after_special_discount: Optional[str] = None
    old_up: Optional[str] = None
    delta: Optional[str] = None
    final_total_price_after_discount: Optional[str] = None
    fv_percent_as_per_rrb: Optional[str] = None
    fv: Optional[str] = None
    total_fv_sar: Optional[str] = None
    revised_fv_percent: Optional[str] = None
    fv_unit_price_after_descope: Optional[str] = None
    to_go_contract_price_eur: Optional[str] = None
    r_ssp_eur: Optional[str] = None


class PriceBookUpdate(BaseModel):
    project_name: Optional[str] = None
    merge_poline_uplline: Optional[str] = None
    po_number: Optional[str] = None
    customer_item_type: Optional[str] = None
    local_content: Optional[str] = None
    scope: Optional[str] = None
    sub_scope: Optional[str] = None
    po_line: Optional[str] = None
    upl_line: Optional[str] = None
    merge_po_poline_uplline: Optional[str] = None
    vendor_part_number_item_code: Optional[str] = None
    po_line_item_description: Optional[str] = None
    zain_item_category: Optional[str] = None
    serialized: Optional[str] = None
    active_or_passive: Optional[str] = None
    uom: Optional[str] = None
    quantity: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    discount: Optional[str] = None
    unit_price_before_discount: Optional[str] = None
    po_total_amt_before_discount: Optional[str] = None
    special_discount: Optional[str] = None
    claimed_percentage_after_special_discount: Optional[str] = None
    unit_price_sar_after_special_discount: Optional[str] = None
    old_up: Optional[str] = None
    delta: Optional[str] = None
    final_total_price_after_discount: Optional[str] = None
    fv_percent_as_per_rrb: Optional[str] = None
    fv: Optional[str] = None
    total_fv_sar: Optional[str] = None
    revised_fv_percent: Optional[str] = None
    fv_unit_price_after_descope: Optional[str] = None
    to_go_contract_price_eur: Optional[str] = None
    r_ssp_eur: Optional[str] = None


class PriceBookResponse(BaseModel):
    id: int
    project_name: Optional[str] = None
    merge_poline_uplline: Optional[str] = None
    po_number: Optional[str] = None
    customer_item_type: Optional[str] = None
    local_content: Optional[str] = None
    scope: Optional[str] = None
    sub_scope: Optional[str] = None
    po_line: Optional[str] = None
    upl_line: Optional[str] = None
    merge_po_poline_uplline: Optional[str] = None
    vendor_part_number_item_code: Optional[str] = None
    po_line_item_description: Optional[str] = None
    zain_item_category: Optional[str] = None
    serialized: Optional[str] = None
    active_or_passive: Optional[str] = None
    uom: Optional[str] = None
    quantity: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    discount: Optional[str] = None
    unit_price_before_discount: Optional[str] = None
    po_total_amt_before_discount: Optional[str] = None
    special_discount: Optional[str] = None
    claimed_percentage_after_special_discount: Optional[str] = None
    unit_price_sar_after_special_discount: Optional[str] = None
    old_up: Optional[str] = None
    delta: Optional[str] = None
    final_total_price_after_discount: Optional[str] = None
    fv_percent_as_per_rrb: Optional[str] = None
    fv: Optional[str] = None
    total_fv_sar: Optional[str] = None
    revised_fv_percent: Optional[str] = None
    fv_unit_price_after_descope: Optional[str] = None
    to_go_contract_price_eur: Optional[str] = None
    r_ssp_eur: Optional[str] = None
    uploaded_by: int
    uploader_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceBookListResponse(BaseModel):
    items: List[PriceBookResponse]
    total: int
    page: int
    page_size: int


class PriceBookBulkUpload(BaseModel):
    """For CSV bulk upload - no additional fields needed"""
    pass
