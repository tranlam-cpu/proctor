import os
from typing import Dict, List, Union, Optional, Any
from dotenv import load_dotenv
from pydantic import BaseSettings, validator

load_dotenv()


class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
   
    
    PROJECT_NAME: str = "Procto Vision"
    PROJECT_DESCRIPTION: str = "Backend API for ProctoVision"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SOCKET_V1_STR: str = "/ws"
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # media
    STATIC_DIR = "media"
    ALLOWED_FORMATS = {'jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024 


    # CORS configuration
    @property
    def ALLOWED_ORIGINS(self) -> list:
        if self.ENVIRONMENT == "production":
            return ["https://localhost:3000"]
        return ["http://localhost:3000","https://localhost:8000", "http://localhost:8000","https://localhost:3000"]

 

    # Database configuration
    DB_ENGINE: str = os.getenv("DB_ENGINE", "mysql") 

    # MySQL configuration
    MYSQL_SERVER: str = os.getenv("MYSQL_SERVER", "localhosts")
    MYSQL_PORT: str = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "proctors")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "123456s")
    
    # Sqlalchemy settings
    # SQLALCHEMY_DATABASE_URI: Optional[str] = None
    # Connection URIs
    MYSQL_DATABASE_URI: Optional[str] = None

    @validator("MYSQL_DATABASE_URI", pre=True)
    def assemble_mysql_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        return (
            
            f"mysql+pymysql://{values.get('MYSQL_USER')}:{values.get('MYSQL_PASSWORD')}@"
            f"{values.get('MYSQL_SERVER')}:{values.get('MYSQL_PORT')}/"
            f"{values.get('MYSQL_DATABASE')}"
        )

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()