# Schemas/ProjectSchema.py
from pydantic import BaseModel

class CreateRANProject(BaseModel):
    pid: str
    po: str
    project_name: str

class UpdateRANProject(BaseModel):
    project_name: str

class RANProjectOUT(CreateRANProject):
    pid_po: str

    class Config:
        orm_mode = True
