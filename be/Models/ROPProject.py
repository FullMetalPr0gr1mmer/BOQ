from sqlalchemy import Enum as SQLAlchemyEnum, String, Column  # Avoid name conflict

from Database.session import Base
from enum import Enum

class CurrencyEnum(str, Enum):
    euros = "Euros"
    dollar = "Dollar"

class ROPProject(Base):
    __tablename__ = 'rop_projects'

    pid_po = Column(String(200), primary_key=True, index=True)
    pid = Column(String(100), index=True)
    po = Column(String(100), index=True)
    project_name = Column(String(200), index=True)
    wps = Column(String(200), unique=True, index=True)
    country = Column(String(200), index=True)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), default=CurrencyEnum.euros, index=True)  # Enum in DB
