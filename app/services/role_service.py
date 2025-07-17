from app.models.base import Vaitro, ChucnangQuyenVaitro
from app.schemas.role import RoleBase
from app.schemas.permission import PermissionBase, PermissionRequest
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import  Any, Optional


def get_permission_service(db: Session,roleID)->Optional[PermissionBase]:
    stmt = select(ChucnangQuyenVaitro).where(ChucnangQuyenVaitro.vai_tro_id == roleID)
    return db.execute(stmt).scalars().all()

def assign_permission_service(db:Session,vai_tro_id: int, data:PermissionRequest)->Optional[int]:
    try:
        values_to_insert = [
            {
                'chuc_nang_id': chuc_nang_name, 
                'vai_tro_id': vai_tro_id,      
                'bitwise': bitwise_value
            }
            for chuc_nang_name, bitwise_value in data.vai_tro_id.items()
        ]

        # MySQL upsert với composite primary key
        from sqlalchemy.dialects.mysql import insert as mysql_insert
        stmt = mysql_insert(ChucnangQuyenVaitro).values(values_to_insert)
        stmt = stmt.on_duplicate_key_update(
            bitwise=stmt.inserted.bitwise
        )

        db.execute(stmt)
        db.commit()

        return len(values_to_insert)
    except Exception as e:
        db.rollback()
        return None

        

def get_role_except_student(db: Session)->Optional[Vaitro]:
    """
    Get all role except by ID
    """
    return db.query(Vaitro).filter(~(Vaitro.ten_vai_tro == 'sinh viên')).all()

def get_all(db: Session)->Optional[RoleBase]:
    """
    Get all role
    """
    return db.execute(select(Vaitro)).scalars().all()

def create_role_service(db: Session, role: RoleBase) -> RoleBase:
    """
    Create a new role
    """
    new_role = Vaitro(**role.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

def update_role_service(db: Session, role_id: int, role: RoleBase) -> Any:
    """
    Update an existing role by ID
    """
    try:
        excluded_ids = [1, 2, 3]
        if role_id in excluded_ids:
            existing_role = None
        else:
            existing_role = db.query(Vaitro).filter(Vaitro.id == role_id).first()
            
        if not existing_role:
            return None
        for key, value in role.dict().items():
            setattr(existing_role, key, value)
        db.commit()
        db.refresh(existing_role)
        return existing_role
    except:
        return None

def delete_role_service(db: Session, role_id: int) -> Optional[int]:
    """
    Delete a role by ID
    """
    try:
        excluded_ids = [1, 2, 3]
        if role_id in excluded_ids:
            existing_role = None
        else:
            existing_role = db.query(Vaitro).filter(Vaitro.id == role_id).first()

        if not existing_role:
            return None
        db.delete(existing_role)
        db.commit()
        return role_id
    except:
        return None