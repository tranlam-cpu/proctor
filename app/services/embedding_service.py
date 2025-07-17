from app.db.handler import QueryExecutor
from app.sql import user_queries
from sqlalchemy.orm import Session
from typing import  Any, Optional
from app.models.base import Nhandien,Nguoidung

def get_embedding_by_id(db: Session,maso: str)->Optional[str]:
    """
    Get embedding by ID
    """
    
    return db.query(Nhandien.embedding_vector).filter(Nhandien.nguoi_dung_id  == maso).scalar()

def insert_new_embedding(db: Session,maso: str,embedding_vector:str,quality_score:float)->Optional[Any]:
    """
    Insert new embedding
    """
    newEmbedding=Nhandien(
        nguoi_dung_id= maso,
        embedding_vector = embedding_vector,
        danh_gia = quality_score
    )

    db.add(newEmbedding)
    db.commit()
    db.refresh(newEmbedding)

def verification_identity(db:Session,predicted_label:str) -> Optional[Any]:
    return db.query(Nguoidung.ho_ten,Nhandien.embedding_vector,Nguoidung.ma_so,Nhandien.danh_gia).join(Nhandien,Nguoidung.ma_so==Nhandien.nguoi_dung_id).filter(Nguoidung.ma_so == predicted_label).all()

def verification_All(db:Session)-> Optional[Any]:
    return db.query(Nguoidung.ho_ten,Nhandien.embedding_vector,Nguoidung.ma_so,Nhandien.danh_gia).join(Nhandien,Nguoidung.ma_so==Nhandien.nguoi_dung_id).all()

def get_person_emmbedding(executor: QueryExecutor)-> dict:
    return executor.execute_query(user_queries.GET_PERSON_EMMBEDING)