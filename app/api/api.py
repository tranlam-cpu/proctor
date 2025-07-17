from fastapi import APIRouter , Depends
from app.api.endpoints import  auth, face, person, role, account, ContinuousAuthFace, quiz, media, Identify, fraud
from app.api.web_endpoints import socket
api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(face.router, prefix="/face", tags=["faceRecognition"])
api_router.include_router(person.router, prefix="/person", tags=["persons"])
api_router.include_router(role.router, prefix="/role", tags=["roles"])
api_router.include_router(account.router, prefix="/account", tags=["accounts"])
api_router.include_router(ContinuousAuthFace.router, prefix="/continuous-auth",tags=["continuousAuth"])
api_router.include_router(quiz.router, prefix="/quiz",tags=["quiz"])
api_router.include_router(media.router, prefix="/image",tags=["upload image"])
api_router.include_router(Identify.router, prefix="/identify",tags=["Identify"])
api_router.include_router(fraud.router, prefix="/fraud",tags=["fraud"])

websocket_router = APIRouter()

websocket_router.include_router(socket.router, prefix="/socket",tags=["SocketConnect"])
