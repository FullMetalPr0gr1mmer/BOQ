import ipaddress
import os
import re
from datetime import datetime
from datetime import timedelta
from typing import Dict, Any
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from starlette import status

from Database.session import Session
from Models.User import User

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
SECRET_KEY=os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username:str,db: Session):
    return db.query(User).filter(User.username == username).first()

def authenticate_user( username:str,
                       password: str,
                       db: Session = Depends(get_db)):

    user = get_user(username,db)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme),db:Session=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token,
                             SECRET_KEY,
                             algorithms=[ALGORITHM]
                             )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username)
    if user is None:
        raise credentials_exception
    return user



def generate_distributions(start_date_str, end_date_str, total_quantity):
    start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
    end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()

    # count months
    months = []
    current = start_date
    while current <= end_date:
        months.append((current.year, current.month))
        current += relativedelta(months=1)

    n_months = len(months)
    per_month = math.ceil(total_quantity / n_months)

    distributions = [
        ROPLvl2DistributionCreate(year=year, month=month, allocated_quantity=per_month)
        for (year, month) in months
    ]
    return distributions

def _parse_interface_name(interface_name: str) -> Dict[str, Any]:
    """
    Parse interface names like:
      "Port 3/5-Port 3/5"
    Return a dict: {'a_slot': int|None, 'a_port': int|None, 'b_slot': int|None, 'b_port': int|None}
    """
    if not interface_name:
        return {"a_slot": None, "a_port": None, "b_slot": None, "b_port": None}

    try:
        # split left/right by first dash (handles " - " or "-")
        left_right = interface_name.split("-", 1)
        left = left_right[0]
        right = left_right[1] if len(left_right) > 1 else ""

        # find the first "num/num" pattern on each side
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
    """Convert a SQLAlchemy ORM row to a plain dict (drops _sa_instance_state). Handles special types."""
    out = {}
    for k, v in getattr(obj, "__dict__", {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, ipaddress.IPv4Address):
            out[k] = str(v)  # <-- convert IPv4Address to string
        else:
            out[k] = v
    return out