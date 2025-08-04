from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, PrimaryKeyConstraint
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
    price = Column(Integer, nullable=True)

    def set_service_type(self, types: list):
        enum_list = [TypeofService(t) if not isinstance(t, TypeofService) else t for t in types]
        self.service_type = json.dumps([r.value for r in enum_list])

    def get_service_type(self) -> list[str]:
        if not self.service_type:
            return []
        return [TypeofService(type_).name for type_ in json.loads(self.service_type)]




class Lvl3(Base):
    __tablename__ = 'lvl3'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(200), ForeignKey("projects.pid_po"), index=True)
    project_name = Column(String(200), index=True)
    item_name = Column(String(200),unique=True, index=True)
    service_type = Column(Text, nullable=True)
    uom = Column(String(200), index=True)
    total_quantity = Column(Integer, nullable=True)
    total_price = Column(Integer, nullable=True)


    def set_service_type(self, types: list):
        enum_list = [TypeofService(t) if not isinstance(t, TypeofService) else t for t in types]
        self.service_type = json.dumps([r.value for r in enum_list])

    def get_service_type(self) -> list[str]:
        if not self.service_type:
            return []
        return [TypeofService(type_).name for type_ in json.loads(self.service_type)]

class ItemsForLvl3(Base):
    __tablename__ = 'items_for_lvl3'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(200), ForeignKey("projects.pid_po"), index=True)
    item_name = Column(String(200),ForeignKey("lvl3.item_name"), index=True)
    item_details = Column(String(200))
    vendor_part_number = Column(String(200), index=True)
    service_type = Column(Text, nullable=True)
    category = Column(String(200), nullable=True)
    uom = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Integer, nullable=True)

    def set_service_type(self, types: list):
        enum_list = [TypeofService(t) if not isinstance(t, TypeofService) else t for t in types]
        self.service_type = json.dumps([r.value for r in enum_list])

    def get_service_type(self) -> list[str]:
        if not self.service_type:
            return []
        return [TypeofService(type_).name for type_ in json.loads(self.service_type)]



