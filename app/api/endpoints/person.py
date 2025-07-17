import json
from sqlalchemy import or_, and_
from typing import Any, Optional
from app.schemas.person import BulkDeleteRequest, PaginatedResponse, PersonBase, bulkDeletePersonResponse, createPersonRequest, createPersonResponse, deletePersonRef, deletePersonResponse, updatePersonRequest, updatePersonResponse
from app.services.person_service import bulk_delete_by_maso, delete_person_by_maso, get_person_by_role, insert_person_except_student, insert_person_student, update_person_by_maso
from app.models.base import Nguoidung
from app.db.base import get_mysql_db, get_mysql_async_db
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError


router = APIRouter()

@router.post("/bulk-delete",response_model = bulkDeletePersonResponse)
async def buld_delete_person(request: BulkDeleteRequest,db: AsyncSession  = Depends(get_mysql_async_db)):
    """
    Xóa person với array id
    """
    try:
        if not request.ids:
            raise HTTPException(status_code=400, detail="Danh sách ID không được rỗng")
        
        result = await bulk_delete_by_maso(db,request.ids)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể xóa")
        return bulkDeletePersonResponse(
            success=True,
            message=f"Xóa thành công",
            item=result
        )

    except Exception as e:
        return createPersonResponse(
            success=False,
            message=f"Xóa thất bại",
            item=None
        )



@router.delete("/{ma_so}",response_model = deletePersonResponse)
def delete_person(ma_so:str,db: Session = Depends(get_mysql_db)):
    """
    Xóa person
    """
    try:
        result = delete_person_by_maso(db,ma_so)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể xóa")
        
        return deletePersonResponse(
            success=True,
            message=f"Xóa thành công",
            item=deletePersonRef(ma_so = result)
        )
    
    except Exception as e:
        return createPersonResponse(
            success=False,
            message=f"Xóa thất bại",
            item=None
        )

@router.put("/{ma_so}",response_model = updatePersonResponse)
def update_person(ma_so:str,per_update: updatePersonRequest,db: Session = Depends(get_mysql_db)):
    """
    Cập nhật person
    """
    try:
        updatePersonData = per_update.copy(update={"ma_so":ma_so})
        result = update_person_by_maso(db,updatePersonData)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể cập nhật")
        
        return updatePersonResponse(
            success=True,
            message=f"cập nhật thành công",
            item=result
        )
    except Exception as e:
        return createPersonResponse(
            success=False,
            message=f"cập nhật thất bại",
            item=None
        )

@router.post("/",response_model=createPersonResponse)
def create_person(person: createPersonRequest, db: Session = Depends(get_mysql_db)):
    """
    Thêm giáo viên
    """
    try:
        result = insert_person_except_student(db,person)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể thêm mới")
        
        return createPersonResponse(
            success=True,
            message=f"thêm mới thành công",
            item=result
        )
    except Exception as e:
        
        return createPersonResponse(
            success=False,
            message=f"thêm mới thất bại",
            item=None
        )
    
@router.post("/student",response_model=createPersonResponse)
def create_person_st(person: PersonBase, db: Session = Depends(get_mysql_db)):
    """
    Thêm sinh viên
    """
    try:
        
        result = insert_person_student(db,person)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể thêm mới")
        
        return createPersonResponse(
            success=True,
            message=f"thêm mới thành công",
            item=result
        )
    except Exception as e:
        
        return createPersonResponse(
            success=False,
            message=f"thêm mới thất bại",
            item=None
        )

@router.get("/", response_model=PaginatedResponse)
def get_all_persons_by_role(
    db: Session = Depends(get_mysql_db),
    role: Optional[str] = Query('sinh viên'),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    filters: Optional[str] = Query(None),
    sortKey: Optional[str] = Query(None),
    sortDirection: str = Query("asc", regex="^(asc|desc)$")
) -> Any:
    """
    Endpoint tối ưu với logic xử lý role linh hoạt
    
    - **role**: 'sinh viên' -> chỉ lấy sinh viên, khác -> lấy tất cả except sinh viên
    - **limit**: Số record trên mỗi trang (1-1000)
    - **offset**: Số record bỏ qua để phân trang
    - **search**: Từ khóa tìm kiếm toàn cục
    - **filters**: JSON string chứa filters theo cột
    - **sortKey**: Cột để sắp xếp
    - **sortDirection**: Hướng sắp xếp (asc/desc)
    """
    
    try:
        # Chuẩn hóa input parameters
        clean_search = search.strip() if search and search.strip() else None
        clean_role = role.strip() if role else 'sinh viên'
        
        # Parse và validate filters JSON
        validated_filters = {}
        if filters:
            try:
                parsed_filters = json.loads(filters)
                # Chỉ giữ filters có giá trị hợp lệ và column tồn tại
                validated_filters = {
                    key: str(value).strip()
                    for key, value in parsed_filters.items()
                    if _is_valid_filter_value(value) and hasattr(Nguoidung, key)
                }
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid filters JSON format"
                )
        
        # Khởi tạo base query với role logic
        query = get_person_by_role(db, clean_role)
        
        # Áp dụng column filters nếu có
        if validated_filters:
            filter_conditions = []
            for column_name, filter_value in validated_filters.items():
                column = getattr(Nguoidung, column_name)
                # Sử dụng ILIKE cho partial matching (case-insensitive)
                condition = column.ilike(f"%{filter_value}%")
                filter_conditions.append(condition)
            
            # Áp dụng AND logic cho multiple filters
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))
        
        # Áp dụng global search nếu có
        if clean_search:
            # Định nghĩa các columns có thể search
            searchable_columns = ['ma_so', 'ho_ten', 'email', 'gioi_tinh']
            
            search_conditions = [
                getattr(Nguoidung, col_name).ilike(f"%{clean_search}%")
                for col_name in searchable_columns
                if hasattr(Nguoidung, col_name)
            ]
            
            # Áp dụng OR logic cho search across multiple columns
            if search_conditions:
                query = query.filter(or_(*search_conditions))
        
        # Đếm total records trước khi apply pagination
        total_count = query.count()
        
        # Áp dụng sorting
        if sortKey and hasattr(Nguoidung, sortKey):
            column = getattr(Nguoidung, sortKey)
            if sortDirection == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            # Default sorting theo ma_so
            query = query.order_by(Nguoidung.ma_so.asc())
        
        # Áp dụng pagination và lấy results
        persons = query.offset(offset).limit(limit).all()
        
        return PaginatedResponse(
            items=persons,
            total=total_count
        )
        
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Processing error: {str(e)}"
        )
    

def _is_valid_filter_value(value) -> bool:
    """
    Kiểm tra tính hợp lệ của filter value
    
    Args:
        value: Giá trị cần validate
        
    Returns:
        bool: True nếu value hợp lệ
    """
    if value is None:
        return False
    
    # Convert về string và kiểm tra không rỗng
    str_value = str(value).strip()
    return len(str_value) > 0 and str_value.lower() != 'null'
