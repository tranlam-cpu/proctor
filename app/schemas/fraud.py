from pydantic import BaseModel
from typing import  Optional, Any
from datetime import datetime
from typing import List
from app.schemas.response import BaseResponse

class FraudBase(BaseModel):
    id: Optional[int] = None
    diem_gian_lan: Optional[float] = None
    diem_tuong_dong: Optional[float] = None
    duong_dan_anh: Optional[str] = None
    nguoi_dung_id :Optional[str] = None
    nguoi_tao_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class PaginatedResponse(BaseModel):
    items: List[FraudBase]
    total: int

    class Config:
        orm_mode = True

class FraudResponse(BaseResponse[FraudBase]):
    pass

class deleteRef(BaseModel):
    id: int

class deleteFraudResponse(BaseResponse[deleteRef]):
    pass