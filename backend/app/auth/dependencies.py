from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
import pytz
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Union
from enum import Enum
from app.database.session import get_db
from app.models.admin import Admin
from app.models.user import User
from app.core.config import settings

IST = pytz.timezone('Asia/Kolkata')



class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY =  settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(pytz.utc) + expires_delta
    else:
        expire = datetime.now(pytz.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Union[User, Admin]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        role: str = payload.get("role")
        
        if user_id is None or role is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    if role == UserRole.ADMIN.value or role == UserRole.SUPER_ADMIN.value:
        user = db.query(Admin).filter(Admin.id == user_id).first()
    else:
        user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
        
    # Update last login
    user.last_login = datetime.now(pytz.utc)
    db.commit()
    
    return user

async def get_current_admin(
    current_user: Union[User, Admin] = Depends(get_current_user)
) -> Admin:
    if not isinstance(current_user, Admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_super_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_admin