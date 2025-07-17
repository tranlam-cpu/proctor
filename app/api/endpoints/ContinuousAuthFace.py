import base64
import io
import tempfile
import uuid
from PIL import Image
from app.schemas.continuous_auth import AuthInitRequest
from app.services.VerificationTracker_service import global_verification_tracker
from fastapi import APIRouter,HTTPException, Depends, Form
from app.services.faceAuth_service import ContinuousAuthManager
import cv2
import numpy as np
from app.db.base import get_mysql_db
from sqlalchemy.orm import Session
from app.services.connection_service import manager

router = APIRouter()

continuous_auth_manager = ContinuousAuthManager()
def decode_base64_image(base64_string: str):
    """Decode base64 image string to OpenCV format"""
    try:
        # Loại bỏ prefix data URL nếu có
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        
        # Decode base64 sang bytes
        image_data = base64.b64decode(base64_string)
        
        # Mở image với PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Convert PIL Image sang numpy array
        image_array = np.array(image)
        
        # Convert sang format OpenCV (BGR)
        if len(image_array.shape) == 2:  # Grayscale
            opencv_image = cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)
        elif image_array.shape[2] == 3:  # RGB
            opencv_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        elif image_array.shape[2] == 4:  # RGBA
            opencv_image = cv2.cvtColor(image_array, cv2.COLOR_RGBA2BGR)
        else:
            opencv_image = image_array
            
        return opencv_image
        
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid image format: {str(e)}"
        )
    
@router.post("/initialize")
async def initialize_continuous_auth(
    account_id: int = Form(...), 
    room_id: int = Form(...), 
    baseline_image: str = Form(...), 
    db: Session = Depends(get_mysql_db),
):
    try:
        # Decode image
        opencv_image = decode_base64_image(baseline_image)

        # Initialize session
        result = await continuous_auth_manager.initialize_session(
            account_id, room_id, opencv_image, db
        )

        if not result["success"]:
            status_code = 401 if result.get("error_type") == "authentication_failed" else 400
            raise HTTPException(status_code=status_code, detail=result["message"])
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing session: {str(e)}")
    
@router.get("/status/{account_id}")
async def get_verification_status(account_id: int):
    """
    Polling endpoint - client kiểm tra có cần verify không
    """
    return continuous_auth_manager.get_verification_status(account_id)


@router.post("/verify")
async def verify_continuous(
    account_id: int = Form(...), 
    image_base64: str = Form(...)
):
    """
    Verification endpoint - client gửi ảnh để verify
    """
    
    try:
        # Decode verification image
        opencv_image = decode_base64_image(image_base64)
        if opencv_image is None:
            raise HTTPException(status_code=400, detail="Invalid verification image format")
        
        # Process verification
        result = await continuous_auth_manager.process_verification(account_id, opencv_image)
       
        if result["success"] is False:# and result["fraud_score"] <= 0.8:
            session_verify_item={
                #"similarity_score": result["similarity_score"],
                "fraud_score": result["fraud_score"],
                "session_id": str(uuid.uuid4()),
                "image_base64":image_base64,
            }

            await manager.tracking_session_verify(account_id,session_verify_item)

        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing verification: {str(e)}")
    
@router.delete("/session/{account_id}")
async def end_continuous_auth(account_id: int):
    """
    Kết thúc continuous authentication session
    """
    global_verification_tracker.reset_account(account_id)
    await manager.end_session_verify_request(account_id)
    return continuous_auth_manager.end_session(account_id)

# @router.delete("/session/verify/{account_id}")
# async def end_session_verify(account_id: int):
#     """
#     Clean Session verify
#     """
#     await manager.end_session_verify_request(account_id)