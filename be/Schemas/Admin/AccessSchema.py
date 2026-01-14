# Update Schemas/Admin/AccessSchema.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserProjectAccessBase(BaseModel):
    user_id: int
    project_id: str  # Changed to str since it's pid_po
    permission_level: str
    section:int

class UserProjectAccessCreate(UserProjectAccessBase):
    """Schema for creating a new project access record."""
    pass


class UserProjectAccessUpdate(BaseModel):
    """Schema for updating project access."""
    permission_level: str


class UserProjectAccessResponse(BaseModel):
    """Schema for the response after creating a project access record."""
    id: int
    user_id: int
    project_id:Optional[str]=None# Changed to str since it's pid_po
    permission_level: str
    Ranproject_id:Optional[str]=None
    Ropproject_id:Optional[str]=None
    class Config:
        from_attributes = True


class UserWithProjectsResponse(BaseModel):
    """Schema for showing user with their project access."""
    id: int
    username: str
    email: str
    role_name: str
    projects: List[dict]  # List of projects with permission levels
    can_access_approval: bool = False
    can_access_triggering: bool = False
    can_access_logistics: bool = False

    class Config:
        from_attributes = True


class ApprovalStageAccessUpdate(BaseModel):
    """Schema for updating approval stage access permissions."""
    user_id: int
    can_access_approval: Optional[bool] = None
    can_access_triggering: Optional[bool] = None
    can_access_logistics: Optional[bool] = None


class ApprovalStageAccessResponse(BaseModel):
    """Schema for approval stage access response."""
    id: int
    username: str
    can_access_approval: bool
    can_access_triggering: bool
    can_access_logistics: bool

    class Config:
        from_attributes = True
