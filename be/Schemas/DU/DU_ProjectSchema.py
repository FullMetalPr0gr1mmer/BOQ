from pydantic import BaseModel
from typing import Dict, List, Optional


class CreateDUProject(BaseModel):
    """Schema for creating a new DU Project."""
    pid: str
    po: str
    project_name: str


class UpdateDUProject(BaseModel):
    """Schema for updating an existing DU Project."""
    project_name: str


class UpdatePOSchema(BaseModel):
    """Schema for updating the Purchase Order."""
    new_po: str


class UpdatePOResponse(BaseModel):
    """Response schema for PO update operation."""
    old_pid_po: str
    new_pid_po: str
    affected_tables: Dict[str, int]
    total_records_updated: int
    message: str


class DUProjectOut(BaseModel):
    """Schema for returning a DU Project."""
    pid_po: str
    pid: str
    po: str
    project_name: str

    class Config:
        from_attributes = True


class DUProjectPagination(BaseModel):
    """Schema for paginated DU Project responses."""
    records: List[DUProjectOut]
    total: int

    class Config:
        from_attributes = True


class DUProjectPermission(BaseModel):
    """Schema for project permission check response."""
    project_id: str
    permission_level: str
    can_view: bool
    can_edit: bool
    can_delete: bool
    role: str
