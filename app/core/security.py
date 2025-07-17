# Tạo các hàm security cho xử lý password
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
import uuid
from app.models.base import Refreshtokens

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "role": role}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(db: Session,user_id: int) -> str:
    # Tạo refresh token
    token = str(uuid.uuid4())
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expires_at = datetime.utcnow() + expires_delta
    
    # Kiểm tra và thu hồi refresh token cũ
    db_refresh_tokens = db.query(Refreshtokens).filter(
        Refreshtokens.tai_khoan_id == user_id,
        Refreshtokens.thu_hoi.is_not(True)
    ).all()
    
    for db_token in db_refresh_tokens:
        db_token.thu_hoi = True
    
    # Tạo refresh token mới
    db_refresh_token = Refreshtokens(
        token=token,
        thoi_han=expires_at,
        tai_khoan_id=user_id
    )
    db.add(db_refresh_token)
    db.commit()
    
    return token

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password with hashed password
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Get password hash for storage
    """
    return pwd_context.hash(password)
