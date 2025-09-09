from sqlalchemy import Column, Integer, String, Boolean

from Database.session import Base


class RANInventory(Base):
    """
    SQLAlchemy model for RAN Inventory records.
    """
    __tablename__ = "ran_inventory"

    id = Column(Integer, primary_key=True, index=True)
    mrbts = Column(String(200), index=True, nullable=True)
    site_id = Column(String(200), index=True, nullable=True)
    identification_code = Column(String(200), index=True, nullable=True)
    user_label = Column(String(200), nullable=True)
    serial_number = Column(String(200), index=True, nullable=True)
    duplicate = Column(Boolean, default=False)
    duplicate_remarks = Column(String(200), nullable=True)

    def __repr__(self):
        return f"<RANInventory(id={self.id}, site_id='{self.site_id}')>"
