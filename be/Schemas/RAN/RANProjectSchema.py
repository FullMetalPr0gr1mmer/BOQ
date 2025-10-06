# Schemas/ProjectSchema.py
from pydantic import BaseModel
from typing import Dict

class CreateRANProject(BaseModel):
    pid: str
    po: str
    project_name: str

class UpdateRANProject(BaseModel):
    project_name: str

class UpdatePOSchema(BaseModel):
    new_po: str

class UpdatePOResponse(BaseModel):
    old_pid_po: str
    new_pid_po: str
    affected_tables: Dict[str, int]
    total_records_updated: int
    message: str

class RANProjectOUT(CreateRANProject):
    pid_po: str

    class Config:
        orm_mode = True
