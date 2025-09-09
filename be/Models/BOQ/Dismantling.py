from sqlalchemy import Column, Integer, String, Text
from Database.session import Base

class Dismantling(Base):
    __tablename__ = "dismantling"

    id = Column(Integer, primary_key=True, index=True)
    nokia_link_id = Column(String(200), index=True, nullable=False)
    nec_dismantling_link_id = Column(String(200), index=True, nullable=False)
    no_of_dismantling = Column(Integer, nullable=False)
    comments = Column(Text, nullable=True)
