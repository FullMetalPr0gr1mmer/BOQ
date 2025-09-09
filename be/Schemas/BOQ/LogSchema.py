from datetime import datetime
from pydantic import BaseModel


class LogBase(BaseModel):
    user: str
    log: str


class LogCreate(LogBase):
    """Schema for creating a log entry."""
    pass


class LogOut(LogBase):
    """Schema for returning a log entry."""
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
