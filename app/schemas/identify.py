from typing import Any, Optional
from pydantic import BaseModel
from typing import List
from app.schemas.response import BaseResponse
from datetime import datetime

class IdentifyBase(BaseModel):
    id: Optional[int] = None
    nguoi_dung_id: Optional[str] = None
    duong_dan_anh: Optional[str] = None
    danh_gia: Optional[float] = None
    created_at: Optional[datetime] = None

class PaginatedResponse(BaseModel):
    items: List[IdentifyBase]
    total: int

    class Config:
        orm_mode = True

class deleteRef(BaseModel):
    id: int


class deleteIdentifyResponse(BaseResponse[deleteRef]):
    pass

class IdentifyResponse(BaseResponse[IdentifyBase]):
    pass