"""
Core Authentication and Utility Module

This module provides essential authentication, security, and utility functions
used throughout the BOQ management system. It handles JWT token creation and validation,
password hashing, user authentication, and various utility functions for data processing.

Key Components:
1. Authentication & Security:
   - JWT token creation and validation
   - Password hashing using bcrypt
   - OAuth2 authentication scheme
   - User authentication and authorization

2. Utility Functions:
   - Interface name parsing for network equipment
   - Date distribution calculations
   - SQLAlchemy object to dictionary conversion
   - Safe type conversion utilities

Dependencies:
- python-jose: JWT token handling
- passlib: Password hashing
- fastapi.security: OAuth2 implementation
- python-dotenv: Environment variable management

Environment Variables Required:
- SECRET_KEY: JWT signing secret
- ALGORITHM: JWT signing algorithm (typically HS256)
- ACCESS_TOKEN_EXPIRE_MINUTES: Token expiration time

Author: [Your Name]
Created: [Date]
Last Modified: [Date]
"""

import ipaddress
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from starlette import status

from Database.session import Session
from Models.Admin.User import User
from Models.Admin.RefreshToken import RefreshToken
from Models.Admin.TokenBlacklist import TokenBlacklist

# Load environment variables from .env file
load_dotenv()

# Security configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # Password hashing context
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")            # OAuth2 authentication scheme

# JWT configuration from environment variables
SECRET_KEY = os.getenv("SECRET_KEY")                               # Secret key for JWT signing
ALGORITHM = os.getenv("ALGORITHM")                                 # JWT signing algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))  # Access token expiration (30 minutes)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # Refresh token expiration (7 days default)


# ===== AUTHENTICATION FUNCTIONS =====

def verify_password(plain_password, hashed_password):
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password (str): The plain text password to verify
        hashed_password (str): The hashed password to compare against

    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username: str, db: Session):
    """
    Retrieve a user from the database by username.

    Args:
        username (str): The username to search for
        db (Session): Database session

    Returns:
        User: User object if found, None otherwise
    """
    return db.query(User).filter(User.username == username).first()

def get_db():
    """
    Database dependency that provides a database session.
    Ensures proper cleanup of database connections.

    Yields:
        Session: SQLAlchemy database session
    """
    db = Session()
    try:
        yield db
    finally:
        db.close()

def authenticate_user(username: str, password: str, db: Session = Depends(get_db)):
    """
    Authenticate a user with username and password.

    Args:
        username (str): The username to authenticate
        password (str): The plain text password
        db (Session): Database session (injected dependency)

    Returns:
        User: User object if authentication successful, False otherwise
    """
    user = get_user(username, db)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token with the provided data.

    Args:
        data (dict): Data to encode in the token (typically includes 'sub' for username)
        expires_delta (Optional[timedelta]): Custom expiration time, defaults to 15 minutes

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, user_id: int, db: Session) -> str:
    """
    Create a JWT refresh token and store it in the database.

    Refresh tokens are longer-lived than access tokens (7 days vs 30 minutes)
    and allow users to obtain new access tokens without re-authenticating.

    Args:
        data (dict): Data to encode in the token (typically includes 'sub' for username)
        user_id (int): ID of the user this token belongs to
        db (Session): Database session for storing the refresh token

    Returns:
        str: Encoded JWT refresh token
    """
    # Revoke all existing refresh tokens for this user
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})

    # Calculate expiration
    expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta

    # Create token payload
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})

    # Encode token
    encoded_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Store in database
    refresh_token_record = RefreshToken(
        user_id=user_id,
        token=encoded_token,
        expires_at=expire
    )
    db.add(refresh_token_record)
    db.commit()

    return encoded_token


# ===== UTILITY FUNCTIONS =====

def generate_distributions(start_date_str, end_date_str, total_quantity):
    """
    Generate monthly distributions of quantities between start and end dates.

    Args:
        start_date_str (str): Start date in DD.MM.YYYY format
        end_date_str (str): End date in DD.MM.YYYY format
        total_quantity (int): Total quantity to distribute across months

    Returns:
        list: List of ROPLvl2DistributionCreate objects with monthly allocations

    Note: This function has a dependency on ROPLvl2DistributionCreate and
          relativedelta that are not imported in this file.
    """
    start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
    end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()

    # Count months between start and end dates
    months = []
    current = start_date
    while current <= end_date:
        months.append((current.year, current.month))
        current += relativedelta(months=1)  # Note: relativedelta needs to be imported

    # Calculate quantity per month (rounded up)
    n_months = len(months)
    per_month = math.ceil(total_quantity / n_months)  # Note: math needs to be imported

    # Create distribution objects
    distributions = [
        ROPLvl2DistributionCreate(year=year, month=month, allocated_quantity=per_month)
        for (year, month) in months
    ]
    return distributions

def _parse_interface_name(interface_name: str) -> Dict[str, Any]:
    """
    Parse network interface names and extract slot/port information.

    Parses interface names in the format "Port 3/5-Port 3/5" and extracts
    slot and port numbers for both sides of the connection.

    Args:
        interface_name (str): Interface name string to parse

    Returns:
        Dict[str, Any]: Dictionary containing:
            - a_slot (int|None): First slot number
            - a_port (int|None): First port number
            - b_slot (int|None): Second slot number
            - b_port (int|None): Second port number

    Example:
        >>> _parse_interface_name("Port 3/5-Port 7/2")
        {'a_slot': 3, 'a_port': 5, 'b_slot': 7, 'b_port': 2}
    """
    if not interface_name:
        return {"a_slot": None, "a_port": None, "b_slot": None, "b_port": None}

    try:
        # Split left/right by first dash (handles " - " or "-")
        left_right = interface_name.split("-", 1)
        left = left_right[0]
        right = left_right[1] if len(left_right) > 1 else ""

        # Find the first "num/num" pattern on each side
        m_left = re.search(r'(\d+)\s*/\s*(\d+)', left)
        m_right = re.search(r'(\d+)\s*/\s*(\d+)', right)

        a_slot = int(m_left.group(1)) if m_left else None
        a_port = int(m_left.group(2)) if m_left else None
        b_slot = int(m_right.group(1)) if m_right else None
        b_port = int(m_right.group(2)) if m_right else None

        return {"a_slot": a_slot, "a_port": a_port, "b_slot": b_slot, "b_port": b_port}
    except Exception:
        return {"a_slot": None, "a_port": None, "b_slot": None, "b_port": None}

def _sa_row_to_dict(obj) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy ORM object to a plain dictionary.

    Removes internal SQLAlchemy attributes and handles special data types
    like datetime and IPv4Address objects for JSON serialization.

    Args:
        obj: SQLAlchemy ORM object

    Returns:
        Dict[str, Any]: Plain dictionary representation of the object

    Features:
        - Removes attributes starting with underscore (SQLAlchemy internals)
        - Converts datetime objects to ISO format strings
        - Converts IPv4Address objects to strings
        - Preserves all other attribute types
    """
    out = {}
    for k, v in getattr(obj, "__dict__", {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, ipaddress.IPv4Address):
            out[k] = str(v)  # Convert IPv4Address to string
        else:
            out[k] = v
    return out

def safe_int(value, default=0):
    """
    Safely convert a value to integer with a default fallback.

    Args:
        value: Value to convert to integer
        default (int): Default value if conversion fails (default: 0)

    Returns:
        int: Converted integer or default value

    Example:
        >>> safe_int("123")
        123
        >>> safe_int("invalid", 42)
        42
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# ===== AUTHENTICATION MIDDLEWARE =====

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Get the current authenticated user from JWT token.

    This function is used as a dependency in protected routes to ensure
    the user is authenticated and to retrieve their user information.

    Args:
        token (str): JWT token from Authorization header (injected dependency)
        db (Session): Database session (injected dependency)

    Returns:
        User: Current authenticated user object

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or user not found

    Usage:
        Use as a dependency in FastAPI routes:
        @app.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.username}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Check if token is blacklisted (revoked on logout)
    is_blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception
    return user
