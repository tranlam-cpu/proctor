from pydantic import BaseModel

# Models cho Client-Driven approach
class ContinuousAuthRequest(BaseModel):
    account_id: int
    room_id: str
    image_base64: str
    session_token: str

class AuthStatusResponse(BaseModel):
    should_verify: bool
    session_token: str
    verification_interval: int  # seconds
    fraud_score: float
    status: str
    message: str
    next_check_after: int  # seconds

    class Config:
        orm_mode = True