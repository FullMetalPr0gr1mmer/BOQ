from datetime import timedelta, datetime, timezone
from email_validator import EmailNotValidError
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import validate_email, BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import logging
from APIs.Core import pwd_context, authenticate_user, create_access_token, create_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_db, get_current_user, oauth2_scheme, SECRET_KEY, ALGORITHM
from Schemas.Admin.UserSchema import CreateUser
from Models.Admin.User import User, Role
from Models.Admin.RefreshToken import RefreshToken
from Models.Admin.TokenBlacklist import TokenBlacklist
from Models.Admin.AuditLog import AuditLog
from utils.password_validator import validate_password_strength
from utils.rate_limiter import check_auth_rate_limit

logger = logging.getLogger(__name__)

userRoute = APIRouter(tags=["Users"])


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: str = None,
    resource_name: str = None,
    details: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Create an audit log entry."""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


# --- Pydantic Schemas ---
class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


# --- Registration Endpoint ---
@userRoute.post("/register")
async def register(user: CreateUser, request: Request, db: Session = Depends(get_db)):
    # SECURITY: Rate limit registration attempts to prevent abuse
    client_ip = get_client_ip(request)
    check_auth_rate_limit(client_ip, "register")

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

    # Create audit log for registration
    await create_audit_log(
        db=db,
        user_id=new_user.id,
        action="register",
        resource_type="user",
        resource_id=str(new_user.id),
        resource_name=new_user.username,
        details=f"New user registered: {new_user.username}",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return {"msg": "Registration successful"}


# --- Login Endpoint ---
@userRoute.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # SECURITY: Rate limit login attempts to prevent brute force attacks
    client_ip = get_client_ip(request)
    check_auth_rate_limit(client_ip, "login")

    user = authenticate_user(form_data.username, form_data.password, db=db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

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

    # Create audit log for login
    await create_audit_log(
        db=db,
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.username,
        details=f"User logged in: {user.username}",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role.name
    }


# --- Refresh Token Endpoint ---
@userRoute.post("/auth/refresh")
async def refresh_access_token(
    token_request: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh an access token using a valid refresh token.

    This endpoint allows users to obtain a new access token without re-authenticating,
    providing a seamless user experience while maintaining security.

    Args:
        token_request: Contains the refresh token
        request: FastAPI Request object for IP extraction
        db: Database session

    Returns:
        dict: New access token and same refresh token

    Raises:
        HTTPException: If refresh token is invalid, expired, or revoked
    """
    # SECURITY: Rate limit refresh attempts
    client_ip = get_client_ip(request)
    check_auth_rate_limit(client_ip, "login")  # Use same limit as login

    try:
        # Decode and validate refresh token
        payload = jwt.decode(token_request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Check if token exists in database and is valid
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token == token_request.refresh_token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
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
            "refresh_token": token_request.refresh_token,  # Return same refresh token
            "token_type": "bearer",
            "role": user.role.name
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# --- Logout Endpoint ---
@userRoute.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Logout the current user by blacklisting their access token.

    This endpoint invalidates the user's current access token and all refresh tokens,
    forcing them to re-authenticate to obtain new tokens.

    Args:
        request: FastAPI Request object
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

        # Create audit log for logout
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="logout",
            resource_type="user",
            resource_id=str(current_user.id),
            resource_name=current_user.username,
            details=f"User logged out: {current_user.username}",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        db.commit()

        return {"message": "Successfully logged out"}

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
