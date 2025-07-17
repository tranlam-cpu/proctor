from app.models.base import Nhandien
from app.schemas.identify import IdentifyBase, IdentifyResponse, PaginatedResponse, deleteIdentifyResponse, deleteRef
from app.services.identify_service import delete_identify_service, get_identify_service, update_face_service
from app.services.media_service import upload_image_service
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from app.db.base import get_mysql_db
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
from sqlalchemy import or_, and_

router = APIRouter()

@router.delete("/{id}",response_model = deleteIdentifyResponse)
def delete_person(id:int,db: Session = Depends(get_mysql_db)):
    try:
        result = delete_identify_service(db,id)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể xóa")
        
        return deleteIdentifyResponse(
            success=True,
            message=f"Xóa thành công",
            item=deleteRef(id = result)
        )
    
    except Exception as e:
        return deleteIdentifyResponse(
            success=False,
            message=f"Xóa thất bại",
            item=None
        )

@router.put("/{nguoi_dung_id}/face",response_model = IdentifyResponse)
async def update_password_account(
    nguoi_dung_id:str,
    image: UploadFile = File(...),
    db: Session = Depends(get_mysql_db)):
    try:
        image_data = await image.read()
        image_format = image.filename.split('.')[-1]
        duong_dan_anh = upload_image_service(image_data,image_format)

        result = update_face_service(db,nguoi_dung_id,duong_dan_anh)

        if result is None:
            raise HTTPException(status_code=400, detail="Không thể cập nhật")
        
        return IdentifyResponse(
            success=True,
            message=f"cập nhật thành công",
            item=result
        )
    except Exception as e:
        return IdentifyResponse(
            success=False,
            message=f"cập nhật thất bại",
            item=None
        )

@router.get("/", response_model=PaginatedResponse)
def get_all(
    db: Session = Depends(get_mysql_db),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    filters: Optional[str] = Query(None),
    sortKey: Optional[str] = Query(None),
    sortDirection: str = Query("asc", regex="^(asc|desc)$")
):
    """
    API lấy danh sách với filter, search và pagination
    """
    try:
        # Parse và validate filters trước
        validated_filters = _parse_and_validate_filters(filters)
        
        # Khởi tạo base query bằng service với join sẵn
        query = get_identify_service(db)
        
        # Apply các column filters còn lại
        if validated_filters:
            query = _apply_column_filters(query, validated_filters)
        
        # Apply global search
        clean_search = search.strip() if search and search.strip() else None
        if clean_search:
            query = _apply_global_search(query, clean_search)
        
        # Đếm total records trước pagination
        total_count = query.count()
        
        # Apply sorting
        query = _apply_sorting(query, sortKey, sortDirection)
        
        # Pagination và lấy kết quả
        identify_raw = query.offset(offset).limit(limit).all()

        identify = [
            IdentifyBase(
                id=row[0],
                duong_dan_anh=row[1],
                danh_gia=row[2],
                nguoi_dung_id=row[3],
                created_at=row[4],
            )
            for row in identify_raw
        ]
        
        return PaginatedResponse(
            items=identify,
            total=total_count
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
def _parse_and_validate_filters(filters: Optional[str]) -> Dict[str, Any]:
    """
    Parse và validate filters JSON với mapping field names
    """
    if not filters:
        return {}
    
    try:
        parsed_filters = json.loads(filters)
        validated_filters = {}
        
        # Mapping từ frontend field names sang backend logic
        FIELD_MAPPING = {
            'nguoi_dung_id': 'nguoi_dung_id',          
            'danh_gia': 'danh_gia',
            'id': 'id',
            'created_at': 'created_at',
        }
        
        for key, value in parsed_filters.items():
            if _is_valid_filter_value(value) and key in FIELD_MAPPING:
                mapped_key = FIELD_MAPPING[key]
                validated_filters[mapped_key] = str(value).strip()
        
        return validated_filters
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid filters JSON format"
        )


def _apply_column_filters(query, filters: Dict[str, Any]):
    """
    Apply column filters - service đã có join sẵn với Vaitro
    """
    filter_conditions = []
    
    for field_name, filter_value in filters.items():
        # Xử lý direct columns trên Taikhoan
        if hasattr(Nhandien, field_name):
            column = getattr(Nhandien, field_name)
            condition = column.ilike(f"%{filter_value}%")
            filter_conditions.append(condition)
    
    # Apply AND logic cho tất cả filters
    if filter_conditions:
        query = query.filter(and_(*filter_conditions))
    
    return query


def _apply_global_search(query, search_term: str):
    """
    Apply global search - join với Vaitro đã có sẵn từ service
    """
    # Định nghĩa các columns có thể search
    searchable_fields = [
        Nhandien.nguoi_dung_id,
        Nhandien.id,
        Nhandien.created_at,
        Nhandien.danh_gia
    ]
    
    # Tạo OR conditions cho search
    search_conditions = [
        field.ilike(f"%{search_term}%") 
        for field in searchable_fields
    ]
    
    
    return query.filter(or_(*search_conditions))


def _apply_sorting(query, sort_key: Optional[str], sort_direction: str):
    """
    Apply sorting - join với Vaitro đã có sẵn từ service
    """
    # Mapping sort keys với columns tương ứng
    SORTABLE_FIELDS = {
        'nguoi_dung_id': Nhandien.nguoi_dung_id,
        'id': Nhandien.id,
        'danh_gia': Nhandien.danh_gia,
        'created_at': Nhandien.created_at,
    }
    
    if sort_key and sort_key in SORTABLE_FIELDS:
        column = SORTABLE_FIELDS[sort_key]
        
        if sort_direction == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default sorting theo id
        query = query.order_by(Nhandien.id.asc())
    
    return query


def _is_valid_filter_value(value) -> bool:
    """
    Validate filter value - kiểm tra value không null và không rỗng
    """
    return value is not None and str(value).strip() != ""