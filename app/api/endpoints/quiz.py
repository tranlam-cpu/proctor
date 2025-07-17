from app.schemas.quiz import QuizBase, QuizListResponse, QuizResponse, QuizResponseItem
from app.services.quiz_service import create_quiz_service, delete_quiz_service, get_all_service, update_quiz_service
from fastapi import APIRouter, Depends, HTTPException
from app.db.base import get_mysql_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/", response_model=QuizListResponse )
def get_all(
    db: Session = Depends(get_mysql_db),
    #current_user: Taikhoan = Depends(require_function_permission("person", PERMISSIONS.VIEW))
):
    try:
        quiz = get_all_service(db)
        if not quiz:
            raise HTTPException(status_code=404, detail="No Quiz found")
        return QuizResponse(
                success=True,
                item=[
                    {
                        "id": q.id,
                        "tieu_de": q.tieu_de,
                        "mo_ta": q.mo_ta,
                        "cau_hoi": q.cau_hoi,
                        "thoi_luong": q.thoi_luong,
                        "created_at": q.created_at,
                        "trang_thai": q.trang_thai,
                    }
                    for q in quiz
                ]
            )
    except Exception as e:
        print(e)
        return QuizResponse(
                success=False
            )

@router.post("/", response_model=QuizResponse)
def insert_quiz(
    quiz: QuizBase,
    db: Session = Depends(get_mysql_db),
):
    try:
        if not quiz.tieu_de or not quiz.tieu_de.strip():
            raise HTTPException(status_code=400, detail="không thể thêm đề thi")
        
        new_quiz = create_quiz_service(db, quiz)
        
        if new_quiz is None:
            raise HTTPException(status_code=400, detail="không thể thêm đề thi")
        return QuizResponse(
                success=True,
                item=QuizResponseItem.from_orm(new_quiz),
                message="thêm đề thi thành công"
        )
    except Exception as e:
        return QuizResponse(
                success=False,
                message=f"thêm đề thi thất bại",
            )
    

@router.delete("/{id}",response_model=QuizResponse)
def delete_quiz(
    id: int,
    db: Session = Depends(get_mysql_db)
):
    try:
        result = delete_quiz_service(db,id)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể xóa")
        
        return QuizResponse(
            success=True,
            message=f"Xóa thành công",
            item=result
        )
    
    except Exception as e:
        return QuizResponse(
            success=False,
            message=f"Xóa thất bại",
            item=None
        )
    
@router.put("/{id}",response_model = QuizResponse)
def update_quiz(id:int,quiz_update: QuizBase,db: Session = Depends(get_mysql_db)):
    try:
        result = update_quiz_service(db,id,quiz_update)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể cập nhật")
        
        return QuizResponse(
            success=True,
            message=f"cập nhật thành công",
            item=result
        )
    except Exception as e:
        return QuizResponse(
            success=False,
            message=f"cập nhật thất bại",
            item=None
        )