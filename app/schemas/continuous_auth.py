from pydantic import BaseModel

class AuthInitRequest(BaseModel):
    account_id: int
    room_id: int
    baseline_image: str