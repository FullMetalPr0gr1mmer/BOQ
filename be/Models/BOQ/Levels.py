from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, PrimaryKeyConstraint,Float
from sqlalchemy.orm import relationship

from Database.session import Base
import json

class TypeofService(str, Enum):  # str mixin added for Pydantic compatibility
    Software = "1"
    Hardware = "2"
    Service = "3"
    def __str__(self):
        return self.name

class Lvl1(Base):
    __tablename__ = 'lvl1'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(200), ForeignKey("projects.pid_po"), index=True)
    project_name = Column(String(200),  index=True)
    item_name = Column(String(200), index=True)
    region = Column(String(200), index=True)
    service_type = Column(Text, nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)

    def set_service_type(self, types: list):
        enum_list = [TypeofService(t) if not isinstance(t, TypeofService) else t for t in types]
        self.service_type = json.dumps([r.value for r in enum_list])

    def get_service_type(self) -> list[str]:
        if not self.service_type:
            return []
        return [TypeofService(type_).name for type_ in json.loads(self.service_type)]


#///////////////////////////////////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////////////////////////////////
class Lvl3(Base):
    __tablename__ = 'lvl3'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(200), ForeignKey("projects.pid_po"), index=True)
    project_name = Column(String(200), index=True)
    item_name = Column(String(200), index=True)  # removed unique=True
    _service_type = Column('service_type', String, default='[]')
    uom = Column(String(200), index=True)
    upl_line = Column(String(200), nullable=True)
    total_quantity = Column(Integer, nullable=True)
    total_price = Column(Float, nullable=True)

    # 🔑 establish relationship: one Lvl3 has many ItemsForLvl3
    items = relationship("ItemsForLvl3", back_populates="lvl3", cascade="all, delete-orphan")

    @property
    def service_type(self):
        """Converts the JSON string from the database into a Python list."""
        try:
            return json.loads(self._service_type)
        except (json.JSONDecodeError, TypeError):
            return []

    @service_type.setter
    def service_type(self, value):
        """Converts a Python list into a JSON string for database storage."""
        if isinstance(value, list):
            self._service_type = json.dumps(value)
        else:
            self._service_type = '[]'



class ItemsForLvl3(Base):
    __tablename__ = 'items_for_lvl3'
    id = Column(Integer, primary_key=True, index=True)
    lvl3_id = Column(Integer, ForeignKey("lvl3.id"), nullable=False)
    item_name = Column(String(200), index=True)
    item_details = Column(String(200))
    vendor_part_number = Column(String(200), index=True)

    # Corrected: Use a private column for storage
    _service_type = Column('service_type', Text, nullable=True, default='[]')

    category = Column(String(200), nullable=True)
    uom = Column(Integer, nullable=True)
    upl_line = Column(String(200), nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)

    lvl3 = relationship("Lvl3", back_populates="items")

    @property
    def service_type(self):
        """Converts the JSON string from the database into a Python list."""
        try:
            return json.loads(self._service_type)
        except (json.JSONDecodeError, TypeError):
            return []

    @service_type.setter
    def service_type(self, value):
        """Converts a Python list into a JSON string for database storage."""
        if isinstance(value, list):
            # Ensure values are converted to strings if they come from an enum or something similar
            self._service_type = json.dumps([str(v) for v in value])
        else:
            self._service_type = '[]'