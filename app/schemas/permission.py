from app.schemas.response import BaseResponse
from pydantic import BaseModel
from typing import  Any, Dict, Optional

class PermissionBase(BaseModel):
    vai_tro_id: Optional[int] = None
    chuc_nang_id: Optional[str] = None
    bitwise: Optional[int] = None

    class Config:
        orm_mode = True

class PermissionRequest(BaseModel):
    vai_tro_id: Dict[str, int]

class PermissionResponse(BaseResponse[Any]):
    pass