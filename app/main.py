import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router, websocket_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.config import settings
from app.middlewares.security import SecurityHeadersMiddleware
from fastapi import FastAPI
from pathlib import Path as PathlibPath

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Environment check
app.add_middleware(
    SecurityHeadersMiddleware
)

# Tạo thư mục upload nếu chưa tồn tại
PathlibPath(settings.STATIC_DIR).mkdir(exist_ok=True)

# Mount static files để serve images
app.mount("/media", StaticFiles(directory=settings.STATIC_DIR), name="media")

if settings.ENVIRONMENT == "development":
    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
else:
    # Production: serve React static files
    static_dir = Path(__file__).parent.parent / "dist"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

#In clude Websocket router
app.include_router(websocket_router,prefix=settings.SOCKET_V1_STR)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# Serve React app for production
if settings.ENVIRONMENT == "production":
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        
        static_dir = Path(__file__).parent.parent / "dist"
        file_path = static_dir / full_path
        
        # If file exists, serve it
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Otherwise serve index.html (for React Router)
        return FileResponse(static_dir / "index.html")
else:
    @app.get("/")
    def read_root():
        return {"message": "Hello from FastAPI! Environment: " + settings.ENVIRONMENT}





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, ssl_keyfile="key.pem", ssl_certfile="cert.pem")