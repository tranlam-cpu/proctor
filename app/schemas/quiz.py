from app.schemas.response import BaseResponse
from pydantic import BaseModel
from typing import  Optional, Any, List


class QuizBase(BaseModel):
    id: Optional[int] = None
    tieu_de: Optional[str] = None
    mo_ta: Optional[str] = None
    cau_hoi: Optional[Any] = None
    thoi_luong :Optional[int] = None
    created_at: Optional[Any] = None
    trang_thai: Optional[str] = None

    class Config:
        orm_mode = True

class QuizResponseItem(QuizBase):
    class Config:
        orm_mode = True

class QuizResponse(BaseResponse[QuizResponseItem]):
    pass

class QuizListResponse(BaseResponse[List[QuizResponseItem]]):
    pass
