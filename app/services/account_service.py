from app.models.base import Taikhoan, Vaitro
from app.schemas.account import UpdateAccountRequest, UpdateRole
from app.core.security import get_password_hash
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from typing import  Any, Optional



def get_account_service(db: Session, role_filter: Optional[str] = None):
    try:
        base_query = (
            db.query(*Taikhoan.__table__.c,Vaitro.ten_vai_tro)
            .join(Vaitro, Taikhoan.vai_tro_id == Vaitro.id,isouter=True)
        )
        
        if role_filter:
            base_query = base_query.filter(Vaitro.ten_vai_tro == role_filter)
            
        return base_query
    except Exception as e:
        return db.query(Taikhoan).filter(text("1 = 0"))
    

def update_password_service(db:Session, id: int, update_data:UpdateAccountRequest)->Any:
    existing_account = db.query(Taikhoan).filter(Taikhoan.id == id).first()
    if not existing_account:
            return None
    
    hashed_password = get_password_hash(update_data.mat_khau)

    existing_account.mat_khau = hashed_password
    
    try:
        # Commit thay đổi vào database
        db.commit()
        db.refresh(existing_account)
        return existing_account
    except Exception as e:
        # Rollback nếu có lỗi
        db.rollback()
        return None
    
    
def update_role_service(db:Session, id: int,update_data:UpdateRole)->Any:
    existing_account = db.query(Taikhoan).filter(Taikhoan.id == id).first()
    if not existing_account:
            return None
    
    for key, value in update_data.dict().items():
        setattr(existing_account, key, value)
    try:
        # Commit thay đổi vào database
        db.commit()
        db.refresh(existing_account)
        return existing_account
    except Exception as e:
        # Rollback nếu có lỗi
        db.rollback()
        return None
