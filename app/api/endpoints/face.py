import base64
import io
from PIL import Image 
from app.services.faceRecognition_service import FaceRecognitionSystem
from app.services.embedding_service import get_person_emmbedding
from app.services.media_service import decode_base64_image_upload, upload_image_service
from app.services.face_service import update_url_image
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from app.db.base import get_mysql_db
import cv2
import numpy as np
from app.db.handler import mysql_executor

router = APIRouter()
face_system = FaceRecognitionSystem()


def clean_base64_string(base64_string: str) -> str:
    if "base64," in base64_string:
        return base64_string.split("base64,")[1]
    return base64_string

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
    
@router.post("/detect-faces")
async def detect_faces_endpoint(image: str = Form(...)):
    """Real-time face detection endpoint for auto-capture"""
    try:
        # Decode image
        opencv_image = decode_base64_image(image)
        
        # Detect faces with YOLO
        faces = face_system.detect_faces(opencv_image)
        
        # Format response for frontend
        face_data = []
        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            face_data.append({
                'bbox': {
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                    'width': x2 - x1, 'height': y2 - y1
                },
                'confidence': face['confidence']
            })
        
        return {
            "success": True,
            "faces": face_data,
            "count": len(face_data)
        }
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": f"Detection failed: {str(e)}"}, 
            status_code=500
        )


@router.post("/register-face")
async def register_face_endpoint(
    maso: str = Form(...), 
    db: Session = Depends(get_mysql_db),
    image: str = Form(...)
    ):
    """Register a new face"""
    try:
        # Decode image
        opencv_image = decode_base64_image(image)
        
        # Register face
        result = face_system.register_face(maso, opencv_image, db)
        
        if result["success"]:
            clean_image = clean_base64_string(image)
            image_data, image_format = decode_base64_image_upload(clean_image)
            image_path = upload_image_service(image_data,image_format)
            result_update =  update_url_image(mysql_executor,maso,image_path)

            if result_update is not None:
                return JSONResponse(content=result, status_code=200)

            return JSONResponse(content={"success": False, "message": f"result is None"}, status_code=400)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Registration failed: {str(e)}"}, 
            status_code=500
        )
    
@router.post("/authenticate-face")
async def authenticate_face_endpoint(
    db: Session = Depends(get_mysql_db),
    image: str = Form(...)
    ):
    """Authenticate face"""
    try:
        # Decode image
        opencv_image = decode_base64_image(image)
        
        # Authenticate face
        result = face_system.authenticate_face(db,opencv_image)
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=401)
            
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Authentication failed: {str(e)}"}, 
            status_code=500
        )

@router.get("/users")
async def get_users():
    """Get all registered users"""
    try:
        users=[]
        results = get_person_emmbedding(mysql_executor)
        
        for result in results:
            users.append({
                "ma_so": result["ma_so"],
                "ho_ten": result["ho_ten"],
                "email": result["email"], 
                "face_count": result["face_count"]
            })
        
        return {"users": users}
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to fetch users: {str(e)}"}, 
            status_code=500
        )