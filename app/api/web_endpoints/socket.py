from app.services.user_service import get_user_by_person
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
from app.services.connection_service import manager
router = APIRouter()
from app.db.base import db_handler

@router.websocket("/{mssv}")
async def websocket_endpoint(websocket: WebSocket, mssv: str):
    with db_handler.get_session("mysql") as db:
        account = get_user_by_person(db,mssv)
    
    if not account:
        await websocket.close(code=4004, reason="Invalid MSSV")
        return
    
    # Establish unified connection
    await manager.connect(websocket, mssv, account.id)
    
    try:
        # Background task xử lý messages (kết hợp logic của cả 2 endpoints)
        async def handle_messages():
            while True:
                try:
                    # Timeout mechanism để detect dead connections
                    data = await asyncio.wait_for(
                        websocket.receive_text(), 
                        timeout=30.0
                    )
                    
                    # Parse và validate message
                    try:
                        message = json.loads(data)
                        print(f"📨 Message from {mssv}: {message}")
                    except json.JSONDecodeError:
                        print(f"⚠️ Invalid JSON from {mssv}")
                        continue
                    
                    # Delegate message handling to unified manager
                    await manager.handle_message(mssv, message)
                    
                except asyncio.TimeoutError:
                    # Gửi heartbeat khi timeout (logic từ cả 2 endpoints cũ)
                    await manager.send_heartbeat(mssv)
                    
                except WebSocketDisconnect:
                    print(f"📱 Client {mssv} disconnected normally")
                    break
                    
                except Exception as e:
                    print(f"❌ Message handling error for {mssv}: {e}")
                    break
        
        # Tạo và lưu background task (face logic requirement)
        task = asyncio.create_task(handle_messages())
        manager.connection_tasks[mssv] = task
        
        # Chờ task hoàn thành
        await task
        
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {mssv}")
    except Exception as e:
        print(f"❌ WebSocket error for {mssv}: {e}")
    finally:
        # Comprehensive cleanup cho cả room và face features
        await manager.disconnect(mssv)