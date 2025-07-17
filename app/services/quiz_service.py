from app.schemas.quiz import QuizBase
from app.models.base import Dethi
from sqlalchemy.orm import Session
from typing import  Any, Optional, List
from sqlalchemy import select
from fastapi import HTTPException

def get_all_service(db: Session)->List[Dethi]:
    return db.execute(select(Dethi)).scalars().all()

def create_quiz_service(db: Session, quiz: QuizBase) -> QuizBase:
    new_quiz = Dethi(**quiz.dict())
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    return new_quiz


def delete_quiz_service(db: Session, quiz_id: int) -> Optional[int]:
    try:   
        existing_quiz = db.query(Dethi).filter(Dethi.id == quiz_id).first()

        if not existing_quiz:
            return None
        db.delete(existing_quiz)
        db.commit()
        return quiz_id
    except:
        return None
    
def update_quiz_service(db: Session, quiz_id: int, quiz: QuizBase) -> Optional[Dethi]:
    try:
        # Tìm quiz cần cập nhật
        existing_quiz = db.query(Dethi).filter(Dethi.id == quiz_id).first()
        
        if not existing_quiz:
            return None
        
        # Lọc và cập nhật chỉ các field không None
        update_data = quiz.dict(exclude_unset=True, exclude_none=True)
        
        # Loại bỏ các field không được phép cập nhật
        excluded_fields = {'id', 'created_at'}
        for field in excluded_fields:
            update_data.pop(field, None)
        
        # Cập nhật từng field một cách an toàn
        for key, value in update_data.items():
            if hasattr(existing_quiz, key):
                setattr(existing_quiz, key, value)
        
        db.commit()
        db.refresh(existing_quiz)
        return existing_quiz
        
    except:
        db.rollback()
        return None