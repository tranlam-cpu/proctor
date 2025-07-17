from collections import defaultdict
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.models.base import Taikhoan
from app.schemas.user import UserCreate, UserUpdate
from app.sql import user_queries
from app.db.handler import QueryExecutor

def get_user_permissions(executor: QueryExecutor,vai_tro_id: int)-> dict:
    results = executor.execute_query(user_queries.GET_FEATURE_PERMISSION,{"vai_tro_id":vai_tro_id})

    # Xử lý kết quả thành dictionary
    permissions_dict = defaultdict(list)
    
    for row in results:
        #permissions_dict[row['ten_chuc_nang']].append(row['ten_quyen'])
        permissions_dict[row['ten_chuc_nang']] = row['ten_quyen']
    
    return dict(permissions_dict)

def get_user(db: Session,id: str) -> Optional[Taikhoan]:
    """
    Get user by ID
    """
    
    return db.query(Taikhoan).filter(Taikhoan.id  == id).first()

def get_user_by_person(db: Session,maso: str) -> Optional[Taikhoan]:
    """
    Get user by email
    """
    #results = mysql_executor.execute_query(user_queries.GET_USER_BY_EMAIL, {"email": email})
    # return results[0] if results else None
    return db.query(Taikhoan).filter(Taikhoan.nguoi_dung_id == maso).first()

def get_users(db: Session,skip: int = 0, limit: int = 100) -> List[Taikhoan]:
    """
    Get list of users
    """
    return db.query(Taikhoan).offset(skip).limit(limit).all()

def create_user(db: Session,obj_in: UserCreate) -> Taikhoan:
    """
    Create new user
    """
    # Check if user already exists
    db_user = get_user_by_person(db, maso=obj_in.nguoi_dung_id)
    if db_user:
        raise ValueError(f"người dùng có mã số {obj_in.nguoi_dung_id} đã tồn tại")
        
    # Create user object
    db_obj = Taikhoan(
        mat_khau=get_password_hash(obj_in.mat_khau),
        nguoi_dung_id=obj_in.nguoi_dung_id,
        vai_tro_id=obj_in.vai_tro_id
    )
    
    # Add to database
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_user(
    db: Session,
    db_obj: Taikhoan, obj_in: Union[UserUpdate, Dict[str, Any]]
) -> Taikhoan:
    """
    Update user
    """
    # Convert to dict if not already
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.dict(exclude_unset=True)
    
    # Handle password update if needed
    if "mat_khau" in update_data and update_data["mat_khau"]:
        hashed_password = get_password_hash(update_data["mat_khau"])
        del update_data["mat_khau"]
        update_data["hashed_password"] = hashed_password
    
    # Update user
    for field in update_data:
        if hasattr(db_obj, field):
            setattr(db_obj, field, update_data[field])
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_user(db: Session, id: int) -> Taikhoan:
    """
    Delete user
    """
    user = db.query(Taikhoan).get(id)
    if not user:
        raise ValueError(f"Không tìm thấy tài khoản với ID: {id}")
    
    db.delete(user)
    db.commit()
    return user

def authenticate(db: Session, maso: str, password: str) -> Optional[Taikhoan]:
    """
    Authenticate user
    """
    user = get_user_by_person(db, maso=maso)
    if not user:
        return None
    if not verify_password(password, user.mat_khau):
        return None
    return user