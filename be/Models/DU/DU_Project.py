from sqlalchemy import String, Column

from Database.session import Base


class DUProject(Base):
    __tablename__ = 'du_project'
    pid_po = Column(String(200), primary_key=True, index=True)
    pid = Column(String(100), index=True)
    po = Column(String(100), index=True)
    project_name = Column(String(200), index=True)
