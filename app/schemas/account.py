from app.schemas.response import BaseResponse
from pydantic import BaseModel, validator
from typing import List, Optional, Optional
import re

class AccountBase(BaseModel):
    id: Optional[int] = None
    mat_khau: Optional[str] = None
    vai_tro_id: Optional[int] = None
    nguoi_dung_id: Optional[str] = None
    ten_vai_tro: Optional[str] = None


    class Config:
        orm_mode = True

class UpdateRole(BaseModel):
    id:int
    vai_tro_id: int

class UpdateAccountRequest(BaseModel):
    id: int
    mat_khau: str

    @validator('mat_khau')
    def password_update_validation(cls, v):
        if v is None:
            return v  # Cho phép không cập nhật mật khẩu

        if len(v) < 8:
            raise ValueError("ít nhất 8 ký tự")

        if not re.search(r'[a-z]', v):
            raise ValueError("có ít nhất 1 chữ thường")

        if not re.search(r'[A-Z]', v):
            raise ValueError("có ít nhất 1 chữ hoa")

        if not re.search(r'\d', v):
            raise ValueError("có ít nhất 1 chữ số")

        if not re.search(r'[\W_]', v):  # \W = non-word character, _ thêm nếu bạn muốn chấp nhận nó là ký tự đặc biệt
            raise ValueError("có ít nhất 1 ký tự đặc biệt")

        return v

class AccountResponse(BaseResponse[AccountBase]):
    pass

class PaginatedResponse(BaseModel):
    items: List[AccountBase]
    total: int

    class Config:
        orm_mode = True