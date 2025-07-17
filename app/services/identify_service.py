from sqlalchemy.orm import Session
from typing import Optional
from app.models.base import Nhandien
from sqlalchemy import text

def get_identify_service(db: Session)-> str:
    try:
        base_query = (
            db.query(Nhandien.id,Nhandien.duong_dan_anh,Nhandien.danh_gia,Nhandien.nguoi_dung_id,Nhandien.created_at)
        )
             
        return base_query
    except Exception as e:
        return db.query(Nhandien).filter(text("1 = 0"))

def update_face_service(db:Session, nguoi_dung_id: str,duong_dan_anh:str ):
    existing_account = db.query(Nhandien).filter(Nhandien.nguoi_dung_id == nguoi_dung_id).first()
    if not existing_account:
            return None
    
    existing_account.duong_dan_anh = duong_dan_anh
   
    try:
        # Commit thay đổi vào database
        db.commit()
        db.refresh(existing_account)
        return existing_account
    except Exception as e:
        # Rollback nếu có lỗi
        db.rollback()
        return None

def delete_identify_service(db:Session, id: int) -> Optional[int]:
    """
    Delete Person by ma_so
    """
    dbIdentifyById = db.query(Nhandien).filter(Nhandien.id == id).first()

    if not dbIdentifyById:
        return None
    try:
        db.delete(dbIdentifyById)
        db.commit()

        return id
    except:
        return None