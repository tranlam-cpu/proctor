from app.schemas.response import BaseResponse
from pydantic import BaseModel
from typing import  Optional


class RoleBase(BaseModel):
    id: Optional[int] = None
    ten_vai_tro: Optional[str] = None

    class Config:
        orm_mode = True

class deleteRoleRef(BaseModel):
    id: int

class RoleResponse(BaseResponse[RoleBase]):
    pass