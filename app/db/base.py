import os
from typing import Dict, Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager, asynccontextmanager
from app.config import settings

# Base class cho các models
Base = declarative_base()

class DatabaseConfig:
    """Configuration cho từng loại database"""
    
    @staticmethod
    def get_mysql_uri() -> str:
        """Tạo MySQL connection string"""
        return (
            settings.MYSQL_DATABASE_URI
        )
    
    @staticmethod
    def get_mysql_async_uri() -> str:
        """Tạo MySQL async connection string"""
        uri = settings.MYSQL_DATABASE_URI
        # Chuyển driver từ pymysql sang aiomysql cho async
        if uri.startswith("mysql+pymysql"):
            return uri.replace("mysql+pymysql", "mysql+aiomysql")
        elif uri.startswith("mysql://"):
            return uri.replace("mysql://", "mysql+aiomysql://")
        return uri
    
    @staticmethod
    def get_engine_args(db_type: str) -> dict:
        """Lấy các tham số cho engine dựa trên loại database"""
        base_args = {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_size": 10,
            "max_overflow": 20,
        }
        
        if db_type == "mssql":
            base_args["connect_args"] = {"TrustServerCertificate": "yes"}
            
        return base_args
    
    @staticmethod
    def get_async_engine_args(db_type: str) -> dict:
        """Lấy tham số cho async engine"""
        return {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_size": 10,
            "max_overflow": 20,
            "echo": False,  # Tắt debug cho production
        }

class DatabaseConnection:
    """Class quản lý một kết nối database"""
    
    def __init__(self, connection_uri: str, db_type: str = "mysql"):
        self.db_type = db_type
        self.engine = create_engine(
            connection_uri,
            **DatabaseConfig.get_engine_args(db_type)
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager để lấy session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def create_tables(self):
        """Tạo tables từ models"""
        Base.metadata.create_all(self.engine)

class AsyncDatabaseConnection:
    """Class quản lý async database connection"""
    
    def __init__(self, connection_uri: str, db_type: str = "mysql"):
        self.db_type = db_type
        self.async_engine = create_async_engine(
            connection_uri,
            **DatabaseConfig.get_async_engine_args(db_type)
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine,
            expire_on_commit=False,
            class_=AsyncSession
        )
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager để lấy session"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()
    
    async def create_tables(self):
        """Tạo tables async từ models"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

class MultiDatabaseHandler:
    """
    Singleton pattern để quản lý nhiều database connections
    Hỗ trợ cả ORM và SQL thuần, sync và async
    """
    
    _instance = None
    _connections: Dict[str, DatabaseConnection] = {}
    _async_connections: Dict[str, AsyncDatabaseConnection] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_connections()
        return cls._instance
    
    def _initialize_connections(self):
        """Khởi tạo tất cả connections"""
        # MySQL sync connection (giữ nguyên logic cũ)
        mysql_uri = DatabaseConfig.get_mysql_uri()
        self._connections["mysql"] = DatabaseConnection(mysql_uri, "mysql")
        
        # MySQL async connection (thêm mới)
        mysql_async_uri = DatabaseConfig.get_mysql_async_uri()
        self._async_connections["mysql"] = AsyncDatabaseConnection(mysql_async_uri, "mysql")
        
        # Default connection
        default_db = os.getenv("DEFAULT_DB", "mysql")
        self._connections["default"] = self._connections[default_db]
        self._async_connections["default"] = self._async_connections[default_db]
    
    # ========== SYNC METHODS (giữ nguyên) ==========
    def get_connection(self, db_name: str = "default") -> DatabaseConnection:
        """Lấy connection theo tên"""
        if db_name not in self._connections:
            raise ValueError(f"Database '{db_name}' không tồn tại")
        return self._connections[db_name]
    
    @contextmanager
    def get_session(self, db_name: str = "default") -> Generator[Session, None, None]:
        """Lấy session cho database cụ thể"""
        connection = self.get_connection(db_name)
        with connection.get_session() as session:
            yield session
    
    def create_all_tables(self):
        """Tạo tables cho tất cả databases"""
        for name, connection in self._connections.items():
            if name != "default":  # Tránh duplicate
                print(f"Creating tables for {name}...")
                connection.create_tables()
    
    # ========== ASYNC METHODS (thêm mới) ==========
    def get_async_connection(self, db_name: str = "default") -> AsyncDatabaseConnection:
        """Lấy async connection theo tên"""
        if db_name not in self._async_connections:
            raise ValueError(f"Async database '{db_name}' không tồn tại")
        return self._async_connections[db_name]
    
    @asynccontextmanager
    async def get_async_session(self, db_name: str = "default") -> AsyncGenerator[AsyncSession, None]:
        """Lấy async session cho database cụ thể"""
        connection = self.get_async_connection(db_name)
        async with connection.get_session() as session:
            yield session
    
    async def create_all_async_tables(self):
        """Tạo tables async cho tất cả databases"""
        for name, connection in self._async_connections.items():
            if name != "default":
                print(f"Creating async tables for {name}...")
                await connection.create_tables()

# Singleton instance
db_handler = MultiDatabaseHandler()

# Dependency functions cho FastAPI
def get_mysql_db() -> Generator[Session, None, None]:
    """Dependency để lấy MySQL session"""
    with db_handler.get_session("mysql") as session:
        yield session

# ========== ASYNC DEPENDENCIES (thêm mới) ==========
async def get_mysql_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency để lấy MySQL async session"""
    async with db_handler.get_async_session("mysql") as session:
        yield session

async def get_async_db(db_name: str = "default") -> AsyncGenerator[AsyncSession, None]:
    """Generic async dependency cho bất kỳ database nào"""
    async with db_handler.get_async_session(db_name) as session:
        yield session