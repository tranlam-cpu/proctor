from app.schemas.fraud import FraudBase
from sqlalchemy.orm import Session
from app.models.base import PhatHienGianLan
from sqlalchemy import text
from typing import Optional

def create_fraud_service(db: Session, fraud: FraudBase) -> FraudBase:
    new_fraud = PhatHienGianLan(**fraud.dict())
    db.add(new_fraud)
    db.commit()
    db.refresh(new_fraud)
    return new_fraud

def get_fraud_service(db: Session)-> str:
    try:
        base_query = (
            db.query(PhatHienGianLan.id,PhatHienGianLan.nguoi_tao_id,PhatHienGianLan.nguoi_dung_id,PhatHienGianLan.duong_dan_anh,PhatHienGianLan.diem_tuong_dong,PhatHienGianLan.diem_gian_lan,PhatHienGianLan.created_at)
        )
             
        return base_query
    except Exception as e:
        return db.query(PhatHienGianLan).filter(text("1 = 0"))
    
def delete_fraud_service(db:Session, id: int) -> Optional[int]:
    """
    Delete fraud by id
    """
    dbIdentifyById = db.query(PhatHienGianLan).filter(PhatHienGianLan.id == id).first()

    if not dbIdentifyById:
        return None
    try:
        db.delete(dbIdentifyById)
        db.commit()

        return id
    except:
        return None