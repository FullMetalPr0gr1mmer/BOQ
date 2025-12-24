from datetime import timedelta, datetime
from email_validator import EmailNotValidError
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import validate_email, BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from APIs.Core import pwd_context, authenticate_user, create_access_token, create_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_db, get_current_user, oauth2_scheme, SECRET_KEY, ALGORITHM
from Schemas.Admin.UserSchema import CreateUser
from Models.Admin.User import User, Role
from Models.Admin.RefreshToken import RefreshToken
from Models.Admin.TokenBlacklist import TokenBlacklist
from utils.password_validator import validate_password_strength

#from APIs.BOQ.LogRoute import create_log
#from Schemas.Admin.LogSchema import LogCreate

userRoute = APIRouter(tags=["Users"])


# --- Pydantic Schemas ---
class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


# --- Registration Endpoint ---
@userRoute.post("/register")
async def register(user: CreateUser, db: Session = Depends(get_db)):
    # Validate email format
    try:
        validate_email(user.email)
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if username or email already exists
    if db.query(User).filter((User.username == user.username) | (User.email == user.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    # Validate password strength
    is_valid, message = validate_password_strength(user.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

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

    # Create access token (30 minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.name},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Create refresh token (7 days)
    refresh_token = create_refresh_token(
        data={"sub": user.username, "role": user.role.name},
        user_id=user.id,
        db=db
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role.name
    }


# --- Refresh Token Endpoint ---
@userRoute.post("/auth/refresh")
async def refresh_access_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh an access token using a valid refresh token.

    This endpoint allows users to obtain a new access token without re-authenticating,
    providing a seamless user experience while maintaining security.

    Args:
        request: Contains the refresh token
        db: Database session

    Returns:
        dict: New access token and same refresh token

    Raises:
        HTTPException: If refresh token is invalid, expired, or revoked
    """
    try:
        # Decode and validate refresh token
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Check if token exists in database and is valid
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token == request.refresh_token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()

        if not token_record:
            raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")

        # Get user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Create new access token
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role.name},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": access_token,
            "refresh_token": request.refresh_token,  # Return same refresh token
            "token_type": "bearer",
            "role": user.role.name
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# --- Logout Endpoint ---
@userRoute.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Logout the current user by blacklisting their access token.

    This endpoint invalidates the user's current access token and all refresh tokens,
    forcing them to re-authenticate to obtain new tokens.

    Args:
        current_user: Current authenticated user (from token)
        token: Current access token
        db: Database session

    Returns:
        dict: Success message

    Raises:
        HTTPException: If token is invalid or already blacklisted
    """
    try:
        # Decode token to get expiration time
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")

        if exp_timestamp is None:
            raise HTTPException(status_code=400, detail="Invalid token format")

        # Convert timestamp to datetime
        expires_at = datetime.fromtimestamp(exp_timestamp)

        # Add access token to blacklist
        blacklisted_token = TokenBlacklist(
            token=token,
            expires_at=expires_at
        )
        db.add(blacklisted_token)

        # Revoke all refresh tokens for this user
        db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).update({"revoked": True})

        db.commit()

        return {"message": "Successfully logged out"}

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
