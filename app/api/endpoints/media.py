from app.services.media_service import decode_base64_image_upload, delete_image_service, upload_image_service
from app.schemas.media import  ImageResponse, ImageUploadRequest
from fastapi import HTTPException, APIRouter, Path
from pathlib import Path as PathlibPath
from app.config import settings

router = APIRouter()

@router.post("/upload", response_model=ImageResponse, summary="Upload base64 image to static")
async def upload_image(request: ImageUploadRequest):
    """
    Upload image từ base64 và lưu vào static directory
    """
    try:
        # Decode base64 image
        image_data, image_format = decode_base64_image_upload(request.image_data)
        
        static_url = upload_image_service(image_data,image_format)
        
        
        return ImageResponse(
            url = static_url,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    

@router.delete("/image/{image_url}", summary="Delete image khỏi static")
async def delete_image(image_url: str):

    file_path = PathlibPath(image_url)
    
    try:
        delete_image_service(file_path)
        
        return {
            "message": "Image đã được xóa thành công",
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")