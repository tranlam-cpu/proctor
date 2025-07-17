from typing import List
from app.schemas.role import RoleBase, RoleResponse, deleteRoleRef
from app.services.role_service import assign_permission_service, create_role_service, delete_role_service, get_all, get_permission_service, get_role_except_student, update_role_service
from app.models.base import Taikhoan
from app.api.middleware import require_function_permission
from app.constants import PERMISSIONS
from app.schemas.permission import PermissionBase, PermissionRequest, PermissionResponse
from fastapi import APIRouter, Depends, HTTPException
from app.db.base import get_mysql_db
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/assign/{vai_tro_id}",response_model=PermissionResponse)
def assgin_permission(
    vai_tro_id: int,
    request : PermissionRequest,
    db: Session = Depends(get_mysql_db),
):
    try:
        new_role = assign_permission_service(db, vai_tro_id,request)
        if new_role is None:
            raise HTTPException(status_code=400, detail="không thể phân quyền")
        return RoleResponse(
                success=True,
                item=new_role,
                message="đăng ký thành công"
        )
    except Exception as e:
        return RoleResponse(
                success=False,
                message=f"đăng ký thất bại",
            )


@router.get("/permission/{roleID}",response_model=List[PermissionBase])
def get_permission_by_role(
    roleID:int,
    db: Session = Depends(get_mysql_db),
):
    try: 
        return get_permission_service(db,roleID)
    except Exception as e:
        return HTTPException(status_code=404, detail="No permission found")

@router.get("/", response_model=List[RoleBase] )
def get_all_role_except_student(
    db: Session = Depends(get_mysql_db),
    #current_user: Taikhoan = Depends(require_function_permission("person", PERMISSIONS.VIEW))
):
    return get_role_except_student(db)

@router.get("/all", response_model=RoleResponse)
def get_all_role(
    db: Session = Depends(get_mysql_db),
):
    try:
        roles = get_all(db)
        if not roles:
            raise HTTPException(status_code=404, detail="No roles found")
        return RoleResponse(
                success=True,
                item=roles
            )
    except Exception as e:
        return RoleResponse(
                success=False
            )
    
@router.post("/", response_model=RoleResponse)
def insert_role(
    role: RoleBase,
    db: Session = Depends(get_mysql_db),
):
    try:
        new_role = create_role_service(db, role)
        if new_role is None:
            raise HTTPException(status_code=400, detail="không thể thêm vai trò")
        return RoleResponse(
                success=True,
                item=new_role,
                message="thêm vai trò thành công"
        )
    except Exception as e:
        return RoleResponse(
                success=False,
                message=f"thêm vai trò thất bại",
            )
    
@router.delete("/{id}",response_model=RoleResponse)
def delete_role(
    id: int,
    db: Session = Depends(get_mysql_db)
):
    try:
        result = delete_role_service(db,id)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể xóa")
        
        return RoleResponse(
            success=True,
            message=f"Xóa thành công",
            item=deleteRoleRef(id = result)
        )
    
    except Exception as e:
        return RoleResponse(
            success=False,
            message=f"Xóa thất bại",
            item=None
        )
    
@router.put("/{id}",response_model = RoleResponse)
def update_person(id:int,role_update: RoleBase,db: Session = Depends(get_mysql_db)):
    """
    Cập nhật person
    """
    try:
        result = update_role_service(db,id,role_update)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể cập nhật")
        
        return RoleResponse(
            success=True,
            message=f"cập nhật thành công",
            item=result
        )
    except Exception as e:
        return RoleResponse(
            success=False,
            message=f"cập nhật thất bại",
            item=None
        )