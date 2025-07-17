import uuid
from app.config import settings
import base64
import imghdr
from typing import Optional
from pathlib import Path as PathlibPath


def decode_base64_image_upload(base64_string: str):
    """
    Giải mã base64 string thành binary data
    Trả về: (binary_data, format)
    """
    try:
        # Decode base64 string
        image_data = base64.b64decode(base64_string)
        
        # Kiểm tra kích thước file
        if len(image_data) > settings.MAX_FILE_SIZE:
            raise ValueError(f"File quá lớn. Tối đa {settings.MAX_FILE_SIZE / (1024*1024)}MB")
        
        # Xác định định dạng image
        image_format = imghdr.what(None, h=image_data)
        if not image_format or image_format not in settings.ALLOWED_FORMATS:
            raise ValueError(f"Định dạng không được hỗ trợ. Chỉ chấp nhận: {', '.join(settings.ALLOWED_FORMATS)}")
        
        return image_data, image_format
    
    except base64.binascii.Error:
        raise ValueError("Base64 string không hợp lệ")

def generate_unique_filename(original_filename: Optional[str], image_format: str) -> str:
    """
    Tạo filename unique cho static serving
    """
    # Tạo UUID làm filename
    unique_id = str(uuid.uuid4())
    
    # Nếu có original filename, giữ lại extension
    if original_filename:
        original_ext = PathlibPath(original_filename).suffix.lower()
        if original_ext in [f'.{fmt}' for fmt in settings.ALLOWED_FORMATS]:
            return f"{unique_id}{original_ext}"
    
    # Fallback sử dụng detected format
    return f"{unique_id}.{image_format}"

def upload_image_service(image_data:bytes, image_format:str) -> str:
    # Tạo filename unique
    filename = generate_unique_random(image_format)
    file_path = PathlibPath(settings.STATIC_DIR) / filename
    
    # Save file vào static directory
    with open(file_path, 'wb') as f:
        f.write(image_data)      
    
    # URL để truy cập static file
    return f"/media/{filename}"

def delete_image_service(file_path: str)->bool:
    try:
        # Xóa file khỏi static directory
        if file_path.exists():
            file_path.unlink()   
        return True     
    except:
        return None
    
def generate_unique_random(image_format: str) -> str:
    unique_id = uuid.uuid4().hex  # Sinh chuỗi hex ngẫu nhiên
    return f"{unique_id}.{image_format}"


