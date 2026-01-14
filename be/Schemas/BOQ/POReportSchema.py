from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class POReportBase(BaseModel):
    pur_doc: Optional[str] = Field(None, description="Purchase Document")
    customer_site_ref: Optional[str] = Field(None, description="Customer Site Reference")
    project: Optional[str] = Field(None, description="Project")
    so_number: Optional[str] = Field(None, description="Sales Order Number")
    material_des: Optional[str] = Field(None, description="Material Description")
    rr_date: Optional[str] = Field(None, description="RR Date")
    site_name: Optional[str] = Field(None, description="Site Name")
    wbs_element: Optional[str] = Field(None, description="WBS Element")
    supplier: Optional[str] = Field(None, description="Supplier")
    name_1: Optional[str] = Field(None, description="Name 1")
    order_date: Optional[str] = Field(None, description="Order Date")
    gr_date: Optional[str] = Field(None, description="GR Date")
    supplier_invoice: Optional[str] = Field(None, description="Supplier Invoice")
    ir_docdate: Optional[str] = Field(None, description="IR Document Date")
    pstng_date: Optional[str] = Field(None, description="Posting Date")
    po_value_sar: Optional[str] = Field(None, description="PO Value SAR")
    invoiced_value_sar: Optional[str] = Field(None, description="Invoiced Value SAR")
    percent_invoiced: Optional[str] = Field(None, description="Percent Invoiced")
    balance_value_sar: Optional[str] = Field(None, description="Balance Value SAR")
    svo_number: Optional[str] = Field(None, description="SVO Number")
    header_text: Optional[str] = Field(None, description="Header Text")
    smp_id: Optional[str] = Field(None, description="SMP ID")
    remarks: Optional[str] = Field(None, description="Remarks")
    aind: Optional[str] = Field(None, description="AInd")
    accounting_indicator_desc: Optional[str] = Field(None, description="Accounting Indicator Description")

    class Config:
        populate_by_name = True
        from_attributes = True


class POReportCreate(POReportBase):
    pass


class POReportUpdate(BaseModel):
    pur_doc: Optional[str] = None
    customer_site_ref: Optional[str] = None
    project: Optional[str] = None
    so_number: Optional[str] = None
    material_des: Optional[str] = None
    rr_date: Optional[str] = None
    site_name: Optional[str] = None
    wbs_element: Optional[str] = None
    supplier: Optional[str] = None
    name_1: Optional[str] = None
    order_date: Optional[str] = None
    gr_date: Optional[str] = None
    supplier_invoice: Optional[str] = None
    ir_docdate: Optional[str] = None
    pstng_date: Optional[str] = None
    po_value_sar: Optional[str] = None
    invoiced_value_sar: Optional[str] = None
    percent_invoiced: Optional[str] = None
    balance_value_sar: Optional[str] = None
    svo_number: Optional[str] = None
    header_text: Optional[str] = None
    smp_id: Optional[str] = None
    remarks: Optional[str] = None
    aind: Optional[str] = None
    accounting_indicator_desc: Optional[str] = None

    class Config:
        populate_by_name = True
        from_attributes = True


class POReportOut(POReportBase):
    id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class POReportUploadResponse(BaseModel):
    message: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    errors: Optional[list] = []
