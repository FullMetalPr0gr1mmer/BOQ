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

    class Config:
        from_attributes = True
