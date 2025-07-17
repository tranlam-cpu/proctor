from typing import List, Optional
from app.schemas.response import BaseResponse
from pydantic import BaseModel


class PersonBase(BaseModel):
    ma_so: Optional[str] = None
    ho_ten: Optional[str] = None
    email: Optional[str] = None
    gioi_tinh: Optional[int] = None

    class Config:
        orm_mode = True
        
class LoginResponsePerson(PersonBase):
    tai_khoan: Optional[int] = None
    vai_tro: Optional[dict] = None

class createPersonRequest(PersonBase):
    vai_tro_id: Optional[int] = None

class createPersonData(PersonBase):
    tai_khoan: Optional[dict] = None

class BulkDeleteRequest(BaseModel):
    ids: List[str]    
   
class updatePersonRequest(BaseModel):
    ho_ten: Optional[str] = None
    email: Optional[str] = None
    gioi_tinh: Optional[int] = None

class updatePersonData(updatePersonRequest):
    ma_so: str

class deletePersonRef(BaseModel):
    ma_so: str

class bulkDeletePerson(BaseModel):
    deleted_count: int

class createPersonResponse(BaseResponse[createPersonData]):
    pass
class updatePersonResponse(BaseResponse[updatePersonData]):
    pass
class deletePersonResponse(BaseResponse[deletePersonRef]):
    pass
class bulkDeletePersonResponse(BaseResponse[bulkDeletePerson]):
    pass


        
class PaginatedResponse(BaseModel):
    items: List[PersonBase]
    total: int

    class Config:
        orm_mode = True
 

    