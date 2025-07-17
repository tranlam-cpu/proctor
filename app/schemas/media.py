from pydantic import BaseModel, validator
from typing import List

class ImageUploadRequest(BaseModel):
    image_data: str  # base64 string
    
    @validator('image_data')
    def validate_base64_image(cls, v):
        """Kiểm tra tính hợp lệ của base64 image data"""
        try:
            # Xử lý data URL format (data:image/jpeg;base64,...)
            if v.startswith('data:image'):
                # Tách phần header và data
                header, data = v.split(',', 1)
                return data
            return v
        except Exception:
            raise ValueError('Định dạng base64 không hợp lệ')

class ImageResponse(BaseModel):
    url: str

    class Config:
        orm_mode = True

class ImageListResponse(BaseModel):
    images: List[ImageResponse]
    total: int

    class Config:
        orm_mode = True