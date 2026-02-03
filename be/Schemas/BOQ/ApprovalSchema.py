from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ApprovalCreate(BaseModel):
    project_id: str = Field(..., description="ID of MW or RAN project (pid_po)")
    project_type: str = Field(..., description="'Zain MW BOQ' or 'Zain Ran BOQ'")


class ApprovalResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    template_filename: str
    template_file_path: str
    project_id: str
    project_type: str
    stage: str
    status: str
    notes: Optional[str] = None
    smp_id: Optional[str] = None  # Deprecated
    so_number: Optional[str] = None  # Deprecated

    # New multi-SMP fields
    planning_smp_id: Optional[str] = None
    planning_so_number: Optional[str] = None
    implementation_smp_id: Optional[str] = None
    implementation_so_number: Optional[str] = None
    dismantling_smp_id: Optional[str] = None
    dismantling_so_number: Optional[str] = None
    epac_req: Optional[str] = None
    inservice_date: Optional[str] = None

    triggering_file_path: Optional[str] = None
    logistics_file_path: Optional[str] = None
    uploaded_by: int
    uploader_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApprovalListResponse(BaseModel):
    items: List[ApprovalResponse]
    total: int
    page: int
    page_size: int


class ApprovalReject(BaseModel):
    notes: str = Field(..., description="Reason for rejection")


class ApprovalApprove(BaseModel):
    # Deprecated field for backward compatibility
    smp_id: Optional[str] = Field(None, description="Deprecated - use specific SMP fields instead")

    # New multi-SMP fields
    planning_smp_id: Optional[str] = Field(None, description="Planning services SMP ID")
    implementation_smp_id: Optional[str] = Field(None, description="Implementation services SMP ID")
    dismantling_smp_id: Optional[str] = Field(None, description="Dismantling services SMP ID (MW only)")
    epac_req: Optional[str] = Field(None, description="E-PAC Req value")
    inservice_date: Optional[str] = Field(None, description="InService Date value")


class ApprovalUpdate(BaseModel):
    status: Optional[str] = None
    stage: Optional[str] = None
    notes: Optional[str] = None


class BulkLogisticsDownload(BaseModel):
    approval_ids: List[int] = Field(..., description="List of approval IDs to combine")
