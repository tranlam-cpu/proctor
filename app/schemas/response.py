from pydantic import BaseModel
from typing import Optional, Generic, TypeVar

T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: Optional[str] = None
    item: Optional[T] = None
    
    class Config:
        orm_mode = True