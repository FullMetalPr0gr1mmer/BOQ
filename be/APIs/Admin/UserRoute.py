from datetime import timedelta
from email_validator import EmailNotValidError
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import validate_email
from sqlalchemy.orm import Session
from APIs.Core import pwd_context, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_db
from Schemas.Admin.UserSchema import CreateUser
from Models.Admin.User import User, Role

#from APIs.BOQ.LogRoute import create_log
#from Schemas.Admin.LogSchema import LogCreate

userRoute = APIRouter(tags=["Users"])


# --- Registration Endpoint ---
@userRoute.post("/register")
async def register(user: CreateUser, db: Session = Depends(get_db)):
    try:
        validate_email(user.email)
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if db.query(User).filter((User.username == user.username) | (User.email == user.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    hashed = pwd_context.hash(user.password)
    user_role = db.query(Role).filter(Role.name == "user").first()
    if not user_role:
        raise HTTPException(status_code=500, detail="Default 'user' role not found")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed,
        role_id=user_role.id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # log_create = LogCreate(user=user.username, log="User registered")
    # create_log(log_create, db=db)

    return {"msg": "Registration successful"}


# --- Login Endpoint ---
@userRoute.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db=db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # log_create = LogCreate(user=form_data.username, log="New login")
    # create_log(log_create, db=db)

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.name},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer", "role": user.role.name}
