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


class ApprovalUpdate(BaseModel):
    status: Optional[str] = None
    stage: Optional[str] = None
    notes: Optional[str] = None
