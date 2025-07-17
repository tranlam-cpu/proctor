from pydantic import BaseModel
from typing import Optional

from app.schemas.person import LoginResponsePerson


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    message: Optional[str] = None
    data : Optional[LoginResponsePerson]  = None


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    role: Optional[str] = None