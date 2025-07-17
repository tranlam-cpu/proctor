from typing import Optional
from pydantic import BaseModel, validator
from app.schemas.person import PersonBase
import re


class UserBase(BaseModel):
    vai_tro_id: Optional[int] = None
    nguoi_dung_id: Optional[str] = None

class UserCreate(UserBase,PersonBase):
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
    
class UserUpdate(UserBase):
    mat_khau: Optional[str] = None

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