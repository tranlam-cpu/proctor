from typing import Optional
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.config import settings
from app.models.base import Taikhoan, Refreshtokens
from app.schemas.token import TokenPayload
from datetime import datetime
from app.core.security import oauth2_scheme
from app.db.base import get_mysql_db



def get_current_user(
    db: Session = Depends(get_mysql_db), token: str = Depends(oauth2_scheme)
) -> Taikhoan:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(Taikhoan).filter(Taikhoan.id == token_data.sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user




def validate_refresh_token(token: str,db: Session = Depends(get_mysql_db)) -> Optional[Taikhoan]:
    db_token = db.query(Refreshtokens).filter(
        Refreshtokens.token == token,
        Refreshtokens.thu_hoi.is_not(True),
        Refreshtokens.thoi_han > datetime.utcnow()
    ).first()
    
    if not db_token:
        return None
    
    user = db.query(Taikhoan).filter(Taikhoan.id == db_token.tai_khoan_id).first()
    return user