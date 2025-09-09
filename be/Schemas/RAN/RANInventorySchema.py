from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class RANInventoryBase(BaseModel):
    """
    Base schema for RAN Inventory data.
    """
    mrbts: Optional[str] = Field(None, max_length=200)
    site_id: Optional[str] = Field(None, max_length=200)
    identification_code: Optional[str] = Field(None, max_length=200)
    user_label: Optional[str] = Field(None, max_length=200)
    serial_number: Optional[str] = Field(None, max_length=200)
    duplicate: Optional[bool] = False
    duplicate_remarks: Optional[str] = Field(None, max_length=200)

class RANInventoryCreate(RANInventoryBase):
    """
    Schema for creating a new RAN Inventory record.
    """
    pass

class RANInventoryUpdate(RANInventoryBase):
    """
    Schema for updating an existing RAN Inventory record.
    """
    pass

class RANInventoryInDB(RANInventoryBase):
    """
    Schema for RAN Inventory data as it appears in the database.
    """
    id: int
    model_config = ConfigDict(from_attributes=True)

class PaginatedRANInventoryResponse(BaseModel):
    """
    Schema for paginated responses of RAN Inventory records.
    """
    total: int
    records: List[RANInventoryInDB]
