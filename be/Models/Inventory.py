from sqlalchemy import Column, Integer, String, ForeignKey

from Database.session import Base


class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer , primary_key=True,index=True)
    site_id=Column(String(100),ForeignKey("sites.site_id"), index=True)
    site_name=Column(String(100),ForeignKey("sites.site_name"),index=True)
    slot_id = Column(Integer, index=True)
    port_id=Column(Integer, index=True)
    status=Column(String(100),index=True)
    company_id=Column(String(100), index=True)
    mnemonic=Column(String(100),index=True)
    clei_code=Column(String(100),index=True)
    part_no=Column(String(100),index=True)
    software_no=Column(String(100),index=True)
    factory_id=Column(String(100),index=True)
    serial_no=Column(String(100),index=True)
    date_id=Column(String(100),index=True)
    manufactured_date=Column(String(100),index=True)
    customer_field=Column(String(100),index=True)
    license_points_consumed=Column(String(100),index=True)
    alarm_status=Column(String(100),index=True)
    Aggregated_alarm_status=Column(String(100),index=True)