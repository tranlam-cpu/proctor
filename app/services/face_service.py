from typing import  Any
from app.db.handler import QueryExecutor
from app.sql import face_queries

def update_url_image(executor: QueryExecutor,userID:str, path:str) -> Any:
    try:
        return executor.execute_command(face_queries.UPDATE_DUONG_DAN_ANH,{"path":path , "userID": userID})
    except Exception as e:
        return None
