from datetime import datetime
from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional

class BOQReferenceBase(BaseModel):
    linkid: str = Field(..., description="e.g., JIZ0243-JIZ0169")
    interface_name: Optional[str] = Field(None, alias="InterfaceName")
    site_ip_a: Optional[str] = Field(None, alias="SiteIPA")  # <- change here
    site_ip_b: Optional[str] = Field(None, alias="SiteIPB")  # <- and here
    pid_po: Optional[str] = Field(None, alias="PIDPO")
    class Config:
        populate_by_name = True
        from_attributes = True

class BOQReferenceCreate(BOQReferenceBase):
    pass

class BOQReferenceOut(BOQReferenceBase):
    id: str
    created_at: Optional[datetime]
