from app.schemas.person import PersonBase, createPersonData, createPersonRequest, deletePersonRef, updatePersonData
from app.core.security import get_password_hash
from sqlalchemy.orm import Session
from typing import Any, List, Optional
from app.models.base import Nguoidung, Taikhoan
from app.models.base import Vaitro
from sqlalchemy import text, func, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

def get_person_by_ms(db: Session,maso: str) -> Optional[Nguoidung]:
    """
    Get person by ID
    """
    return db.query(Nguoidung).filter(Nguoidung.ma_so  == maso).first()

async def bulk_delete_by_maso(db:AsyncSession, ids: List[str]) -> Optional[int]:
    try:
        check_stmt = select(Nguoidung.ma_so).where(Nguoidung.ma_so.in_(ids))
        existing_result = await db.execute(check_stmt)
        existing_ids = existing_result.scalars().all() 
        
        if not existing_ids:
            return None
        
        delete_stmt = delete(Nguoidung).where(Nguoidung.ma_so.in_(existing_ids))
        result = await db.execute(delete_stmt)

        await db.commit()

        return result.rowcount
    except Exception as e:
        print(f"Lỗi bulk delete: {e}")
        # Rollback khi có lỗi xảy ra
        await db.rollback()
    return None

def delete_person_by_maso(db:Session, ma_so: str) -> Optional[str]:
    """
    Delete Person by ma_so
    """
    dbPerByMaso = db.query(Nguoidung).filter(Nguoidung.ma_so == ma_so).first()

    if not dbPerByMaso:
        return None
    try:
        db.delete(dbPerByMaso)
        db.commit()

        return ma_so
    except:
        return None
    

def update_person_by_maso(db:Session,person_update : updatePersonData)->Optional[Any]:
    """
    Update Person by ma_so
    """
    dbPerByMaso = db.query(Nguoidung).filter(Nguoidung.ma_so == person_update.ma_so).first()

    if not dbPerByMaso:
        return None
    
    try:
        # exclude các field không được truyền lên
        update_data = person_update.dict(exclude_unset=True)

        # Cập nhật các trường hợp lệ
        for field, value in update_data.items():
            setattr(dbPerByMaso, field, value)

        db.add(dbPerByMaso)
        db.commit()
        db.refresh(dbPerByMaso)

        return dbPerByMaso
    except:
        return None


def insert_person_student(db:Session, person_new: PersonBase)-> Optional[createPersonData]:
    """
    Create New Person + Account
    """
    existing_account = db.query(Taikhoan).filter(Taikhoan.nguoi_dung_id == person_new.ma_so).first()
    if not existing_account:
        try:
            person = Nguoidung(**person_new.dict())
            db.add(person)
    
            accout_per = Taikhoan(
                nguoi_dung_id=person_new.ma_so,
                vai_tro_id= 2,
                mat_khau=get_password_hash("Educat@123")
            )
        
            db.add(accout_per)
            db.flush()         
            db.commit()

            return createPersonData(
                ma_so = person_new.ma_so,
                ho_ten = person_new.ho_ten,
                email = person_new.email,
                gioi_tinh = person_new.gioi_tinh,
                tai_khoan = {
                    "id":accout_per.id,
                    "vai_tro_id" : 2
                }
            )
        except Exception as e:
            db.rollback()
            
    return None


def insert_person_except_student(db:Session, person_new: createPersonRequest)-> Optional[createPersonData]:
    """
    Create New Person + Account Except Student
    """
    existing_account = db.query(Taikhoan).filter(Taikhoan.nguoi_dung_id == person_new.ma_so).first()

    if not existing_account:
        try:
            person = Nguoidung(**person_new.dict(exclude={"vai_tro_id"}))

            db.add(person)

            accout_per = Taikhoan(
                nguoi_dung_id=person_new.ma_so,
                vai_tro_id= person_new.vai_tro_id,
                mat_khau=get_password_hash("Educat@123")
            )
        
            db.add(accout_per)
            db.flush()         
            db.commit()

            return createPersonData(
                ma_so = person_new.ma_so,
                ho_ten = person_new.ho_ten,
                email = person_new.email,
                gioi_tinh = person_new.gioi_tinh,
                tai_khoan = {
                    "id":accout_per.id,
                    "vai_tro_id" : person_new.vai_tro_id
                }
            )
        except Exception as e:
            db.rollback()
            
    return None

def get_person_by_role(db: Session, role: str):
    """
    Get person by role với logic linh hoạt và tối ưu:
    - Nếu role = 'sinh viên': chỉ lấy role sinh viên
    - Nếu role != 'sinh viên': lấy tất cả records except sinh viên
    
    Args:
        db: Database session
        role: Vai trò cần filter
        
    Returns:
        SQLAlchemy Query object có thể chain thêm filters
    """
    try:
        # Chuẩn hóa role input để so sánh chính xác
        clean_role = role.strip().lower() if role else 'sinh viên'
        
        # Base query với JOIN để có thể filter theo role
        base_query = (
            db.query(Nguoidung)
            .join(Taikhoan, Nguoidung.ma_so == Taikhoan.nguoi_dung_id)
            .join(Vaitro, Taikhoan.vai_tro_id == Vaitro.id)
        )
        
        if clean_role == 'sinh viên':
            # Chỉ lấy records có role là sinh viên
            filtered_query = base_query.filter(
                func.lower(Vaitro.ten_vai_tro) == 'sinh viên'
            )
        else:
            # Lấy tất cả records EXCEPT sinh viên
            filtered_query = base_query.filter(
                func.lower(Vaitro.ten_vai_tro) != 'sinh viên'
            )
        
        return filtered_query
        
    except Exception as e:
        # Log error để debug (nên sử dụng logger trong production)
        print(f"Error in get_person_by_role: {str(e)}")
        # Trả về empty query để tránh crash application
        return db.query(Nguoidung).filter(text("1 = 0"))
   

