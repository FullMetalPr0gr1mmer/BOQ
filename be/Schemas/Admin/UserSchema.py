from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class RoleBase(BaseModel):
    name: str


class Role(RoleBase):
    id: int

    class Config:
        orm_mode = True


class CreateUser(BaseModel):
    email: str
    password: str
    username: str


class UserBase(BaseModel):
    id: int
    username: str
    email: str
    registered_at: datetime


class UserWithRole(UserBase):
    role: Role

    class Config:
        orm_mode = True


class UserRoleUpdateRequest(BaseModel):
    """Schema for updating user role."""
    user_id: int
    new_role_name: str


class UserRoleUpdateResponse(BaseModel):
    """Schema for role update response."""
    id: int
    username: str
    email: str
    old_role: str
    new_role: str

    class Config:
        from_attributes = True