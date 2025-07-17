from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api import deps
from app.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.schemas.token import Token
from app.services.user_service import (
    authenticate,
    get_user_permissions
)
from app.models.base import Taikhoan, Refreshtokens, Nguoidung
from app.db.base import get_mysql_db
from app.services.person_service import get_person_by_ms
from app.schemas.person import LoginResponsePerson
from app.db.handler import mysql_executor

router = APIRouter()

@router.get("/verify-token")
def verify_token(
    current_user: Taikhoan = Depends(deps.get_current_user)
) -> Any:
    """
    Verify that the access token is valid
    """
    return {"valid": True, "user_id": current_user.id}


@router.post("/login", response_model=Token)
def login(
    response: Response,
    db: Session = Depends(get_mysql_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> dict:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate(
        db, maso=form_data.username, password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    person = get_person_by_ms(db,user.nguoi_dung_id)
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="người dùng không tồn tại",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_permissions = get_user_permissions(mysql_executor,user.vai_tro_id)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, role=user.vai_tro_id, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(db=db, user_id=user.id)
    
    # Thiết lập HTTP-only cookie cho refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # seconds
        httponly=True,      # Không thể truy cập qua JavaScript
        secure=True,       # False cho localhost, True cho production HTTPS
        samesite="none" if settings.ENVIRONMENT == "development" else "lax",  # ✅ None cho cross-origin
        path="/",
        domain=None  # ✅ Không set domain cho localhost        
    )


    person_data = LoginResponsePerson.from_orm(person).dict()
    person_data["vai_tro"] = user_permissions
    person_data["tai_khoan"] = user.id

    return {
        "access_token": access_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "token_type": "bearer",
        "message":"đăng nhập thành công",
        "data":LoginResponsePerson(**person_data)
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_mysql_db)
) -> Any:
    """
    Refresh access token
    """
    # Lấy refresh token từ cookie
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không tồn tại"
        )
    try:
        user = deps.validate_refresh_token(db=db, token=refresh_token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.id, role=user.vai_tro_id, expires_delta=access_token_expires
        )
        #new_refresh_token = create_refresh_token(db=db, user_id=user.id)

        return {
            "access_token": access_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "token_type": "bearer"
        }
    except Exception as e:
        # Xóa cookie nếu có lỗi
        response.delete_cookie("refresh_token", path="/")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ hoặc đã hết hạn"
        )

@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_mysql_db),
    current_user: Taikhoan = Depends(deps.get_current_user),
    refresh_token: str = Body(..., embed=True)
) -> dict:
    """
    Logout user and revoke refresh token
    """
    db_token = db.query(Refreshtokens).filter(
        Refreshtokens.token == refresh_token,
        Refreshtokens.tai_khoan_id == current_user.id,
        Refreshtokens.thu_hoi.is_not(True)
    ).first()
    
    # Xóa refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="none" if settings.ENVIRONMENT == "development" else "lax"
    )

    if db_token:
        db_token.revoked = True
        db.commit()
    
    return {"message": "Đăng xuất thành công"}

# @router.get("/me")
# def get_current_user_info(
#     current_user: Taikhoan = Depends(deps.get_current_user),
#     db: Session = Depends(get_mysql_db)
# ) -> dict:
#     """
#     Lấy thông tin user hiện tại từ access token
#     """
    
#     person = db.query(Nguoidung).filter(
#         Nguoidung.ma_so == current_user.nguoi_dung_id
#     ).first()
    
#     if not person:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Thông tin người dùng không tồn tại"
#         )
    
#     return {
#         "user_id": current_user.id,
#         "ma_so": current_user.nguoi_dung_id,
#         "vai_tro_id": current_user.vai_tro_id,
#         "ho_ten": person.ho_ten,
#         "gioi_tinh": person.gioi_tinh,
#         "email": person.email if hasattr(person, 'email') else None
#     }