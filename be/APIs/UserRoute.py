from datetime import timedelta

from email_validator import EmailNotValidError
from fastapi import APIRouter, Form, HTTPException
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import validate_email

from APIs.Core import get_db, pwd_context, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from Database.session import Session
from Models.User import User
from Schemas.UserSchema import CreateUser

userRoute = APIRouter(tags=["Users"])



# --- Registration Endpoint ---
@userRoute.post("/register")
async def register(user: CreateUser,db:Session=Depends(get_db)):
    if user.code != "all0wMetoReg":
        raise HTTPException(status_code=400, detail="Invalid registration code")
    try:
        validate_email(user.email)
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if db.query(User).filter((User.username == user.username) | (User.email == user.email)).first():
        db.close()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    hashed = pwd_context.hash(user.password)
    user = User(username=user.username, email=user.email, hashed_password=hashed)
    db.add(user)
    db.commit()
    return {"msg": "Registration successful"}
@userRoute.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password,db=db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}
