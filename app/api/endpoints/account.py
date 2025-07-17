from typing import Optional, Dict, Any
from app.services.account_service import get_account_service, update_password_service, update_role_service
from app.models.base import Taikhoan, Vaitro
from app.schemas.account import AccountResponse, PaginatedResponse, UpdateAccountRequest, UpdateRole
from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.base import get_mysql_db
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import json
from datetime import datetime
from typing import List
import asyncio
from app.services.connection_service import manager

router = APIRouter()


@router.post("/trigger-face-registration-Concurrent")
async def trigger_face_registration_optimized(
    account_ids: List[int], 
    batch_size: int = 50,
    max_concurrent_batches: int = 3,
    max_retries: int = 3
):
    async def process_single_user(account_id: int, semaphore: asyncio.Semaphore):
        """Xử lý một user với semaphore control"""
        async with semaphore:
            account_data = {
                "id": account_id,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # Retry logic cho từng user
            for attempt in range(max_retries):
                try:
                    success = await manager.send_face_registration_request(account_id, account_data)
                    return {
                        "account_id": account_id,
                        "status": "sent" if success else "offline",
                        "success": success,
                        "attempts": attempt + 1
                    }
                except Exception as e:
                    if attempt == max_retries - 1:
                        return {
                            "account_id": account_id,
                            "status": "error",
                            "success": False,
                            "error": str(e),
                            "attempts": attempt + 1
                        }
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

    async def process_batch_concurrent(batch_ids: List[int]):
        """Xử lý batch với concurrent control"""
        # Giới hạn concurrent connections trong batch
        semaphore = asyncio.Semaphore(10)
        
        # Chạy tất cả users trong batch song song
        tasks = [process_single_user(account_id, semaphore) for account_id in batch_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Xử lý exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "account_id": None,
                    "status": "error",
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results

    # Chia thành batches
    batches = [account_ids[i:i + batch_size] for i in range(0, len(account_ids), batch_size)]
    
    # Xử lý batches với concurrent control
    batch_semaphore = asyncio.Semaphore(max_concurrent_batches)
    
    async def process_batch_with_control(batch):
        async with batch_semaphore:
            return await process_batch_concurrent(batch)
    
    # Chạy các batches song song (có giới hạn)
    batch_tasks = [process_batch_with_control(batch) for batch in batches]
    batch_results = await asyncio.gather(*batch_tasks)
    
    # Flatten kết quả
    all_results = []
    for batch_result in batch_results:
        all_results.extend(batch_result)
    
    successful_count = sum(1 for r in all_results if r["success"])
    
    return {
        "message": f"Processed {len(account_ids)} users in {len(batches)} batches",
        "successful": successful_count,
        "failed": len(account_ids) - successful_count,
        "batches_processed": len(batches),
        "concurrent_batches": max_concurrent_batches,
        "details": all_results
    }

@router.post("/trigger-face-registration")
async def trigger_face_registration(account_id: int):
    # API endpoint để trigger việc đăng ký khuôn mặt
    account_data = {
        "id": account_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Gửi yêu cầu đến user cụ thể
    success = await manager.send_face_registration_request(account_id, account_data)
    
    if success:
        return {"message": f"Face registration request sent to user {account_id}"}
    else:
        return {"error": f"User {account_id} is not online"}, 404


@router.put("/{id}/role",response_model = AccountResponse)
def update_password_account(id:int,request: UpdateRole,db: Session = Depends(get_mysql_db)):
    try:
        result = update_role_service(db,id,request)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể cập nhật")
        
        return AccountResponse(
            success=True,
            message=f"cập nhật thành công",
            item=result
        )
    except Exception as e:
        return AccountResponse(
            success=False,
            message=f"cập nhật thất bại",
            item=None
        )

@router.put("/{id}/password",response_model = AccountResponse)
def update_password_account(id:int,request: UpdateAccountRequest,db: Session = Depends(get_mysql_db)):
    try:
        result = update_password_service(db,id,request)
        if result is None:
            raise HTTPException(status_code=400, detail="Không thể cập nhật")
        
        return AccountResponse(
            success=True,
            message=f"cập nhật thành công",
            item=result
        )
    except Exception as e:
        return AccountResponse(
            success=False,
            message=f"cập nhật thất bại",
            item=None
        )

@router.get("/", response_model=PaginatedResponse)
def get_all_account(
    db: Session = Depends(get_mysql_db),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    filters: Optional[str] = Query(None),
    sortKey: Optional[str] = Query(None),
    sortDirection: str = Query("asc", regex="^(asc|desc)$")
):
    """
    API lấy danh sách tài khoản với filter, search và pagination
    """
    try:
        # Parse và validate filters trước
        validated_filters = _parse_and_validate_filters(filters)
        
        # Trích xuất role filter để pass vào service
        role_filter = None
        if validated_filters and 'role' in validated_filters:
            role_filter = validated_filters['role']
            # Xóa role khỏi filters để tránh apply 2 lần
            del validated_filters['role']
        
        # Khởi tạo base query bằng service với join sẵn
        query = get_account_service(db, role_filter)
        
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
        accounts = query.offset(offset).limit(limit).all()
        
        return PaginatedResponse(
            items=accounts,
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
            'ten_vai_tro': 'role',          # Map về role để xử lý ở service
            'nguoi_dung_id': 'nguoi_dung_id',
            'id': 'id',
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
        if hasattr(Taikhoan, field_name):
            column = getattr(Taikhoan, field_name)
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
        Taikhoan.nguoi_dung_id,
        # Có thể thêm các fields khác như email, ten_hien_thi...
    ]
    
    # Tạo OR conditions cho search
    search_conditions = [
        field.ilike(f"%{search_term}%") 
        for field in searchable_fields
    ]
    
    # Search trong ten_vai_tro - join đã có từ service
    search_conditions.append(Vaitro.ten_vai_tro.ilike(f"%{search_term}%"))
    
    return query.filter(or_(*search_conditions))


def _apply_sorting(query, sort_key: Optional[str], sort_direction: str):
    """
    Apply sorting - join với Vaitro đã có sẵn từ service
    """
    # Mapping sort keys với columns tương ứng
    SORTABLE_FIELDS = {
        'nguoi_dung_id': Taikhoan.nguoi_dung_id,
        'id': Taikhoan.id,
        'ten_vai_tro': Vaitro.ten_vai_tro  # Join đã có sẵn từ service
    }
    
    if sort_key and sort_key in SORTABLE_FIELDS:
        column = SORTABLE_FIELDS[sort_key]
        
        if sort_direction == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default sorting theo id
        query = query.order_by(Taikhoan.id.asc())
    
    return query


def _is_valid_filter_value(value) -> bool:
    """
    Validate filter value - kiểm tra value không null và không rỗng
    """
    return value is not None and str(value).strip() != ""