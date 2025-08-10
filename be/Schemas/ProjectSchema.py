# Schemas/ProjectSchema.py
from pydantic import BaseModel

class CreateProject(BaseModel):
    pid: str
    po: str
    project_name: str

class UpdateProject(BaseModel):
    project_name: str

class Project(CreateProject):
    pid_po: str

    class Config:
        orm_mode = True
