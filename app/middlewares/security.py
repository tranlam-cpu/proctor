from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Bảo mật headers cho cookies
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Cookie security
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = \
                "max-age=31536000; includeSubDomains"
        
        return response