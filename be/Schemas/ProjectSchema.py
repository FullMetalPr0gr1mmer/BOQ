from fastapi import Form
from pydantic import BaseModel,EmailStr
from sqlalchemy import Integer, DateTime


class CreateProject(BaseModel):
    pid:str
    po:str
    project_name:str
class Project(CreateProject):
    pid_po:str
class Config:
    orm_mode = True