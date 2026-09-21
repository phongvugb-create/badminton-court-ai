from datetime import datetime, timedelta
from typing import Optional, Union, Any
try:
    from jose import jwt
    _has_jose = True
except ImportError:
    jwt = None
    _has_jose = False

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    pwd_context = None

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config import settings

try:
    import bcrypt
    _use_direct_bcrypt = True
except ImportError:
    _use_direct_bcrypt = False

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Support plain password matching for mock/quick demo users if not hashed
    if hashed_password and not hashed_password.startswith("$2b$") and not hashed_password.startswith("$2a$"):
        return plain_password == hashed_password
    if _use_direct_bcrypt:
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
        except Exception:
            pass
    try:
        return pwd_context.verify(plain_password[:72], hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    if _use_direct_bcrypt:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8')[:72], salt).decode('utf-8')
    return pwd_context.hash(password[:72])

def create_access_token(subject: Union[str, Any], role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None
