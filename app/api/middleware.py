from app.constants import PERMISSIONS
from app.models.base import Taikhoan
from app.api import deps
from app.services.user_service import get_user_permissions
from fastapi import Depends, HTTPException, status
from app.db.handler import mysql_executor


def require_function_permission(chuc_nang: str, required_permission: PERMISSIONS):
    """
    Middleware kiểm tra quyền trên chức năng cụ thể
    """
    def permission_checker(current_user: Taikhoan = Depends(deps.get_current_user)):
        # Lấy permissions dict của user
        user_permissions = get_user_permissions(mysql_executor,current_user.vai_tro_id)

        # Kiểm tra user có access vào chức năng này không
        if chuc_nang not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. No permission for function: {chuc_nang}"
            )

        # Bitwise check quyền cụ thể
        user_perm_value = user_permissions[chuc_nang]
        if not (user_perm_value & required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required {required_permission.name} permission for {chuc_nang}"
            )
        
        return current_user
    return permission_checker

# Helper dependency trả về tất cả permissions
def get_all_user_permissions(current_user: Taikhoan = Depends(deps.get_current_user)):
    """Dependency inject tất cả permissions để xử lý logic phức tạp"""
    return get_user_permissions(current_user)