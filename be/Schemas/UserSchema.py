from fastapi import Form
from pydantic import BaseModel,EmailStr
from sqlalchemy import Integer, DateTime


class CreateUser(BaseModel):
    email: str
    password: str
    username:  str
    code:str
    role : str ='user'
class User(CreateUser):
    id:int
    registered_at: str

class Config:
    orm_mode = True

