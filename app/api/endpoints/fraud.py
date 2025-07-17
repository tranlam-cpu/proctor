from app.schemas.fraud import FraudBase, FraudResponse, PaginatedResponse, deleteFraudResponse, deleteRef
from app.services.fraud_service import create_fraud_service, delete_fraud_service, get_fraud_service
from app.services.media_service import decode_base64_image_upload, upload_image_service
from app.models.base import PhatHienGianLan
from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.base import get_mysql_db
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
from sqlalchemy import or_, and_

router = APIRouter()


def clean_base64_string(base64_string: str) -> str:
    if "base64," in base64_string:
        return base64_string.split("base64,")[1]
    return base64_string

@router.post("/", response_model=FraudResponse)
def insert_fraud(
    fraud: FraudBase,
    db: Session = Depends(get_mysql_db),
):
    try:
        clean_image = clean_base64_string(fraud.duong_dan_anh)
        image_data, image_format = decode_base64_image_upload(clean_image)
        image_path = upload_image_service(image_data,image_format)

        fraud.duong_dan_anh = image_path
        new_fraud = create_fraud_service(db, fraud)
        
        if new_fraud is None:
            raise HTTPException(status_code=400, detail="không thể thêm")
        return FraudResponse(
                success=True,
                item=new_fraud,
                message="thêm thành công"
        )
    except Exception as e:
        print(e)
        return FraudResponse(
                success=False,
                message=f"thêm thất bại",
            )
    

@router.delete("/{id}",response_model = deleteFraudResponse)
def delete_person(id:int,db: Session = Depends(get_mysql_db)):
    try:
        result = delete_fraud_service(db,id)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể xóa")
        
        return deleteFraudResponse(
            success=True,
            message=f"Xóa thành công",
            item=deleteRef(id = result)
        )
    
    except Exception as e:
        return deleteFraudResponse(
            success=False,
            message=f"Xóa thất bại",
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
        query = get_fraud_service(db)
        
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
            FraudBase(
                id=row[0],
                nguoi_tao_id=row[1],
                nguoi_dung_id=row[2],
                duong_dan_anh=row[3],
                diem_tuong_dong=row[4],
                diem_gian_lan=row[5],
                created_at=row[6],
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
            'id': 'nguoi_dung_id',          
            'nguoi_tao_id': 'danh_gia',
            'nguoi_dung_id': 'id',
            'duong_dan_anh': 'created_at',
            'diem_tuong_dong': 'created_at',
            'diem_gian_lan': 'created_at',
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
        if hasattr(PhatHienGianLan, field_name):
            column = getattr(PhatHienGianLan, field_name)
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
        PhatHienGianLan.nguoi_tao_id,
        PhatHienGianLan.nguoi_dung_id,
        PhatHienGianLan.created_at,
        PhatHienGianLan.diem_tuong_dong,
        PhatHienGianLan.diem_gian_lan
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
        'nguoi_tao_id': PhatHienGianLan.nguoi_tao_id,
        'nguoi_dung_id': PhatHienGianLan.nguoi_dung_id,
        'created_at': PhatHienGianLan.created_at,
        'diem_tuong_dong': PhatHienGianLan.diem_tuong_dong,
        'diem_gian_lan': PhatHienGianLan.diem_gian_lan,
    }
    
    if sort_key and sort_key in SORTABLE_FIELDS:
        column = SORTABLE_FIELDS[sort_key]
        
        if sort_direction == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default sorting theo id
        query = query.order_by(PhatHienGianLan.id.asc())
    
    return query


def _is_valid_filter_value(value) -> bool:
    """
    Validate filter value - kiểm tra value không null và không rỗng
    """
    return value is not None and str(value).strip() != ""