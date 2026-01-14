import json
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from Database.session import Base
from Models.RAN.RANProject import RanProject
class TypeofService(str, Enum):
    Software = "1"
    Hardware = "2"
    Service = "3"
    def __str__(self):
        return self.name

class RANLvl3(Base):
    __tablename__ = 'ranlvl3'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(200), ForeignKey('ran_projects.pid_po'), index=True,nullable=True)
    item_name = Column(String(200), index=True)
    key = Column(String(200), nullable=True)  # New 'key' attribute
    _service_type = Column('service_type', String, default='[]')
    uom = Column(String(200), index=True)
    total_quantity = Column(Integer, nullable=True)
    total_price = Column(Float, nullable=True)
    po_line=Column(String(100), nullable=True)
    items = relationship("ItemsForRANLvl3", back_populates="ranlvl3", cascade="all, delete-orphan")
    category = Column(String(200), nullable=True)
    upl_line=Column(String(100), nullable=True)
    ran_category = Column(String(100), nullable=True)
    sequence = Column(Integer, nullable=True)

    @property
    def service_type(self):
        try:
            return json.loads(self._service_type)
        except (json.JSONDecodeError, TypeError):
            return []

    @service_type.setter
    def service_type(self, value):
        if isinstance(value, list):
            self._service_type = json.dumps(value)
        else:
            self._service_type = '[]'

class ItemsForRANLvl3(Base):
    __tablename__ = 'items_for_ranlvl3'
    id = Column(Integer, primary_key=True, index=True)
    ranlvl3_id = Column(Integer, ForeignKey("ranlvl3.id"), nullable=False)
    item_name = Column(String(200), index=True)
    item_details = Column(String(200))
    vendor_part_number = Column(String(200), index=True)
    _service_type = Column('service_type', Text, nullable=True, default='[]')
    category = Column(String(200), nullable=True)
    uom = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    upl_line=Column(String(100), nullable=True)
    ranlvl3 = relationship("RANLvl3", back_populates="items")

    @property
    def service_type(self):
        try:
            return json.loads(self._service_type)
        except (json.JSONDecodeError, TypeError):
            return []

    @service_type.setter
    def service_type(self, value):
        if isinstance(value, list):
            self._service_type = json.dumps([str(v) for v in value])
        else:
            self._service_type = '[]'