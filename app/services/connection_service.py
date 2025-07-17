import base64
from datetime import datetime
from app.services.VerificationTracker_service import global_verification_tracker
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from typing import Dict, Set, List
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # Unified connections với mssv làm primary key
        self.active_connections: Dict[str, WebSocket] = {}  # mssv -> WebSocket
        
        # Room management 
        self.room_participants: Dict[int, Set[str]] = {}    # room_id -> set of mssv
        
        # Face registration mapping 
        self.mssv_to_account: Dict[str, int] = {}           # mssv -> account_id
        self.connection_tasks: Dict[str, asyncio.Task] = {} # mssv -> Task

        # Quiz control state
        self.quiz_sessions: Dict[int, dict] = {}   # quiz_id -> session info

        #Submit quizz
        self.quiz_submissions: Dict[int, Set[str]] = {}  # quiz_id -> set of submitted mssv

        #Session Verify
        self.session_verify: Dict[int, List[dict]] = {} #account_id -> session verify
        self.session_images = {}

        
    async def connect(self, websocket: WebSocket, mssv: str, account_id: int):
        """Kết nối unified WebSocket cho cả room và face features"""
        # Đóng connection cũ nếu tồn tại
        if mssv in self.active_connections:
            await self.disconnect(mssv)

        await websocket.accept()
        
        # Lưu connection và mapping
        self.active_connections[mssv] = websocket
        self.mssv_to_account[mssv] = account_id
        print(self.mssv_to_account)
        
        print(f"✅ Unified connection established: {mssv} (Account: {account_id})")

    async def disconnect(self, mssv: str):
        """Ngắt kết nối an toàn với comprehensive cleanup"""
        # FIX: Kiểm tra sự tồn tại trước khi xóa để tránh KeyError
        if mssv in self.active_connections:
            websocket = self.active_connections[mssv]
            
            try:
                # Kiểm tra trạng thái trước khi đóng
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close(code=1000)
                    print(f"🔌 Connection gracefully closed: {mssv}")
                else:
                    print(f"⚠️ Connection already closed: {mssv}")
            except Exception as e:
                print(f"⚠️ Connection cleanup warning for {mssv}: {e}")
            finally:
                # Sử dụng pop() thay vì del để tránh KeyError
                self.active_connections.pop(mssv, None)
        
        # Cancel background tasks (face logic) - sử dụng pop() để an toàn
        if mssv in self.connection_tasks:
            try:
                self.connection_tasks[mssv].cancel()
            except Exception as e:
                print(f"⚠️ Task cancellation warning for {mssv}: {e}")
            finally:
                self.connection_tasks.pop(mssv, None)
            
        # Cleanup account mapping (face logic) - sử dụng pop() để an toàn
        self.mssv_to_account.pop(mssv, None)
        
        # Cleanup user khỏi tất cả rooms (room logic)
        await self._cleanup_user_from_rooms(mssv)

    # === ROOM MANAGEMENT FEATURES  ===
    
    async def join_room(self, mssv: str, room_id: int):
        """Tham gia room và cập nhật số lượng real-time"""
        if room_id not in self.room_participants:
            self.room_participants[room_id] = set()
            
        self.room_participants[room_id].add(mssv)
        print(f"🏠 {mssv} joined room {room_id}")

        # Auto-sync quiz state cho student mới join
        await self.send_quiz_state_to_student(mssv, room_id)
        
        # Broadcast số lượng người tham gia
        await self.broadcast_room_count(room_id)

    async def leave_room(self, mssv: str, room_id: int):
        """Rời room và cập nhật số lượng"""
        if room_id in self.room_participants:
            self.room_participants[room_id].discard(mssv)
            print(f"🚪 {mssv} left room {room_id}")
            await self.broadcast_room_count(room_id)

    async def broadcast_room_count(self, room_id: int):
        """Gửi thông tin số lượng người tham gia với error handling"""
        count = len(self.room_participants.get(room_id, set()))
        message = {
            "type": "room_count_update",
            "room_id": room_id,
            "participant_count": count
        }
        
        failed_connections = []
        
        # Gửi message cho tất cả người trong room
        for mssv in self.room_participants.get(room_id, set()):
            if mssv in self.active_connections:
                try:
                    await self.active_connections[mssv].send_text(json.dumps(message))
                except Exception as e:
                    print(f"❌ Failed to send room update to {mssv}: {e}")
                    failed_connections.append(mssv)
        
        # Cleanup failed connections
        for mssv in failed_connections:
            await self.disconnect(mssv)

    async def _cleanup_user_from_rooms(self, mssv: str):
        """Remove user khỏi tất cả rooms và broadcast update"""
        rooms_to_update = []
        
        for room_id, participants in self.room_participants.items():
            if mssv in participants:
                participants.discard(mssv)
                rooms_to_update.append(room_id)
        
        # Broadcast count update cho các rooms bị ảnh hưởng
        for room_id in rooms_to_update:
            await self.broadcast_room_count(room_id)

    # === FACE REGISTRATION FEATURES  ===
    
    async def send_face_registration_request(self, account_id: int, account_data: dict):
        """Gửi face registration request qua unified connection"""
        # Tìm mssv từ account_id
        print(self.mssv_to_account)
        target_mssv = None
        for mssv, stored_account_id in self.mssv_to_account.items():
            if stored_account_id == account_id:
                target_mssv = mssv
                break
        print(f"🔍 Searching for mssv with account_id {account_id}: Found {target_mssv}")
        if target_mssv and target_mssv in self.active_connections:
            try:
                message = {
                    "type": "face_registration_request",
                    "account_data": account_data
                }
                await self.active_connections[target_mssv].send_text(json.dumps(message))
                print(f"📤 Face registration request sent to {target_mssv}")
                return True
            except Exception as e:
                print(f"❌ Failed to send face request to {target_mssv}: {e}")
                await self.disconnect(target_mssv)
        
        print(f"❌ Face registration failed: Account {account_id} not connected")
        return False

    # === SESSION VERIFY FEATURES  ====
    async def tracking_session_verify(self, account_id: int, session_data: dict):
        """Lưu Verify False vào session""" 

        if account_id not in self.session_verify:
            self.session_verify[account_id] = []

        image_base64 = session_data.pop("image_base64", None)

        self.session_verify[account_id].append(session_data)
        
        interval_result = self.get_session_verify_every_nth(account_id, 3)

        if interval_result["success"]:
            selected_session = interval_result["session"]
            target_mssv = None
            
            for mssv, stored_account_id in self.mssv_to_account.items():
                if stored_account_id == account_id:
                    target_mssv = mssv
                    break

            if target_mssv and target_mssv in self.active_connections:
                try:
                    message = {
                        "type": "tracking_verify_request",
                        "session": selected_session
                    }
                    message["session"]["mssv"] = target_mssv
                    message["session"]["has_image"] = bool(selected_session.get("session_id"))

                    if image_base64:
                        session_id = message["session"]["session_id"]
                        self.session_images[session_id] = image_base64
                    
                    student_room_id = None
                    for room_id, participants in self.room_participants.items():
                        if target_mssv in participants:
                            student_room_id = room_id
                            break

                    teacher_mssv = None
                    if student_room_id in self.quiz_sessions:
                        teacher_mssv = self.quiz_sessions[student_room_id]["teacher"]
                    if global_verification_tracker.should_allow_call(account_id, session_data["fraud_score"]):
                        await self.active_connections[teacher_mssv].send_text(json.dumps(message))
                    return True
                except Exception as e:
                    await self.disconnect(target_mssv)
        return False


    def get_session_verify_every_nth(self, account_id: int, interval: int = 3) -> dict:
        """
        Lấy session mỗi interval lần
        """

        sessions = self.session_verify[account_id]
        total_sessions = len(sessions)
        if total_sessions % interval == 0 and total_sessions >= interval:
            target_index = total_sessions - interval
            return {
                "success": True,
                "session": sessions[target_index],
            }
        return{
            "success":False,
            "session":None
        }

    async def send_session_image(self,mssv:str,session_id: str):
        """Gửi hình ảnh qua WebSocket binary khi được yêu cầu"""
        if mssv not in self.active_connections:
            return
        
        if session_id not in self.session_images:
            return
        
        try:
            image_base64 = self.session_images[session_id]

            session_id_bytes = session_id.encode('utf-8')
            session_id_length = len(session_id_bytes)
            image_bytes = image_base64.encode('utf-8')  # Convert string to bytes

            # Tạo header cho binary message
            message = (
                session_id_length.to_bytes(4, 'big') + 
                session_id_bytes +                     
                image_bytes                             
            )

    
            # Gửi binary data
            await self.active_connections[mssv].send_bytes(message)
        except:
            await self.disconnect(mssv)
       

    # === QUIZ CONTROL FEATURES ===
    async def handle_quiz_control(self, mssv: str, message: dict):
        """Xử lý quiz control messages từ teacher"""
        action = message.get("action")
        quiz_id = message.get("quiz_id")
        
        if not quiz_id:
            print(f"⚠️ Quiz control missing quiz_id from {mssv}")
            return
            
        
        if action == "START_QUIZ":
            duration = message.get("duration", 60)
            await self.start_quiz(quiz_id, duration, mssv)
            
        elif action == "PAUSE_QUIZ":
            await self.pause_quiz(quiz_id)
            
        elif action == "RESUME_QUIZ":
            await self.resume_quiz(quiz_id)
            
        elif action == "END_QUIZ":
            await self.end_quiz(quiz_id)
        
        else:
            print(f"⚠️ Unknown quiz action: {action}")

    async def start_quiz(self, quiz_id: int, duration: int, teacher_mssv: str):
        """Start quiz và broadcast cho students"""

        if quiz_id in self.quiz_sessions:
            print(f"⚠️ Quiz {quiz_id} already exists, replacing...")

        self.quiz_sessions[quiz_id] = {
            "status": "active",
            "start_time": datetime.now().timestamp(),
            "duration": duration * 60,  # Convert to seconds
            "remaining_time": duration * 60,
            "teacher": teacher_mssv,
            "original_duration": duration 
        }
        
        # Broadcast START signal
        await self.broadcast_quiz_signal(quiz_id, {
            "type": "quiz_control",
            "signal": "START",
            "quiz_id": quiz_id,
            "duration": duration * 60,
            "remaining_time": duration * 60,
            "timestamp": datetime.now().timestamp()
        })
        
        print(f"🚀 Quiz {quiz_id} started by {teacher_mssv} for {duration} minutes")

    async def pause_quiz(self, quiz_id: int):
        """Pause quiz và lưu remaining time"""
        if quiz_id not in self.quiz_sessions:
            print(f"⚠️ Quiz {quiz_id} not found")
            return
            
        session = self.quiz_sessions[quiz_id]
        if session["status"] == "active":
            # Calculate remaining time
            elapsed = datetime.now().timestamp() - session["start_time"]
            remaining = max(0, session["duration"] - elapsed)
            remaining_seconds = int(remaining)

            session["status"] = "paused"
            session["remaining_time"] = remaining_seconds
            session["pause_time"] = datetime.now().timestamp()
            
            # Broadcast PAUSE signal
            await self.broadcast_quiz_signal(quiz_id, {
                "type": "quiz_control",
                "signal": "PAUSE",
                "quiz_id": quiz_id,
                "remaining_time": remaining_seconds,
                "timestamp": datetime.now().timestamp()
            })
            
            print(f"⏸️ Quiz {quiz_id} paused with {remaining:.0f} seconds remaining")

    async def resume_quiz(self, quiz_id: int):
        """Resume quiz với remaining time"""
        if quiz_id not in self.quiz_sessions:
            print(f"⚠️ Quiz {quiz_id} not found")
            return
            
        session = self.quiz_sessions[quiz_id]
        if session["status"] == "paused":
            session["status"] = "active"
            session["start_time"] = datetime.now().timestamp()
            session["duration"] = session["remaining_time"]
            
            # Broadcast RESUME signal
            await self.broadcast_quiz_signal(quiz_id, {
                "type": "quiz_control",
                "signal": "RESUME",
                "quiz_id": quiz_id,
                "remaining_time": session["remaining_time"],
                "timestamp": datetime.now().timestamp()
            })
            
            print(f"▶️ Quiz {quiz_id} resumed with {session['remaining_time']:.0f} seconds")

    async def end_quiz(self, quiz_id: int):
        """End quiz và cleanup"""
        if quiz_id in self.quiz_sessions:
            # Broadcast END signal
            await self.broadcast_quiz_signal(quiz_id, {
                "type": "quiz_control",
                "signal": "END",
                "quiz_id": quiz_id,
                "timestamp": datetime.now().timestamp()
            })
            
            # Cleanup session
            self.quiz_sessions.pop(quiz_id, None)
            
            print(f"🏁 Quiz {quiz_id} ended and cleaned up")

    # === Boardcast ===

    async def broadcast_quiz_signal(self, quiz_id: int, message: dict):
        """Broadcast quiz control signal to all participants in the room"""
        participants = self.room_participants.get(quiz_id, set())
        failed_connections = []
        
        print(f"📡 Broadcasting quiz signal to {len(participants)} participants in room {quiz_id}")
        
        for mssv in participants:
            if mssv in self.active_connections:
                try:
                    await self.active_connections[mssv].send_text(json.dumps(message))
                    print(f"  ✓ Sent to {mssv}")
                except Exception as e:
                    print(f"  ✗ Failed to send quiz signal to {mssv}: {e}")
                    failed_connections.append(mssv)
        
        # Cleanup failed connections
        for mssv in failed_connections:
            await self.disconnect(mssv)

    async def broadcast_to_all(self, message: dict):
        """Gửi tin nhắn đến tất cả active connections"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected_users = []
        
        # Gửi đến tất cả connections
        for mssv, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                print(f"❌ Failed to send to {mssv}: {e}")
                disconnected_users.append(mssv)
        
        # Cleanup failed connections
        for mssv in disconnected_users:
            await self.disconnect(mssv)

    async def send_quiz_state_to_student(self, mssv: str, quiz_id: int):
        """Gửi current quiz state cho student mới join"""
        if quiz_id not in self.quiz_sessions:
            return
            
        session = self.quiz_sessions[quiz_id]
        
        # Calculate current remaining time
        if session["status"] == "active":
            elapsed = datetime.now().timestamp() - session["start_time"]
            remaining_time = max(0, session["duration"] - elapsed)
            remaining_seconds = int(remaining_time)
            if remaining_time <= 0:
                await self.end_quiz(quiz_id)
                return
                
        else:
            remaining_time = session.get("remaining_time", 0)
        
        message = {
            "type": "quiz_state_sync",
            "quiz_id": quiz_id,
            "status": session["status"],
            "remaining_time": remaining_seconds,
            "timestamp": datetime.now().timestamp()
        }
        
        if mssv in self.active_connections:
            try:
                await self.active_connections[mssv].send_text(json.dumps(message))
                print(f"📤 Quiz state sent to new participant {mssv}")
            except Exception as e:
                print(f"❌ Failed to send quiz state to {mssv}: {e}")

    # === Auto-End Quiz  ====
    async def handle_student_submit(self, mssv: str, quiz_id: int, score: int):
        """Xử lý submit và kiểm tra điều kiện auto-end quiz"""
        
        # Track submission để tránh duplicate
        if quiz_id not in self.quiz_submissions:
            self.quiz_submissions[quiz_id] = set()
        
        # Nếu đã submit rồi thì bỏ qua
        if mssv in self.quiz_submissions[quiz_id]:
            print(f"⚠️ {mssv} already submitted quiz {quiz_id}")
            return
        
        # Thêm vào danh sách đã submit
        self.quiz_submissions[quiz_id].add(mssv)
        
        # Đếm participants và submissions
        participants = self.room_participants.get(quiz_id, set())
        total_participants = len(participants)
        submitted_count = len(self.quiz_submissions[quiz_id])
        
        # thời gian bắt đầu
        start_time = self.quiz_sessions[quiz_id]["start_time"]

        print(f"📋 {mssv} submitted quiz {quiz_id} ({submitted_count}/{total_participants})")
        
        # Broadcast submission notification
        await self.broadcast_student_submission(quiz_id, {
            "student_mssv": mssv,
            "score": score,
            "start_time": start_time,
            "end_time": datetime.now().timestamp(),
            "submitted_count": submitted_count,
            "total_participants": total_participants
        })
        
        # ✅ AUTO-END nếu tất cả đã submit
        if submitted_count >= total_participants-1 and total_participants > 0:
            await self.auto_end_quiz(quiz_id, "all_students_submitted")

    async def auto_end_quiz(self, quiz_id: int, reason: str):
        """Tự động kết thúc quiz"""
        if quiz_id not in self.quiz_sessions:
            return
        
        # Broadcast AUTO_END signal với lý do
        await self.broadcast_quiz_signal(quiz_id, {
            "type": "quiz_control",
            "signal": "AUTO_END",
            "quiz_id": quiz_id,
            "reason": reason,
            "message": "Bài thi đã tự động kết thúc" + (
                " - Tất cả học sinh đã nộp bài" if reason == "all_students_submitted" 
                else " - Hết thời gian"
            ),
            "timestamp": datetime.now().timestamp()
        })
        
        # Cleanup session và submissions
        self.quiz_sessions.pop(quiz_id, None)
        self.quiz_submissions.pop(quiz_id, None)
        
        print(f"🏁 Quiz {quiz_id} auto-ended: {reason}")

    # === CLEAN SESSION VERIFY ====
    async def end_session_verify_request(self,account_id:int):
        if account_id not in self.session_verify:
            return
        
        sessions_to_clean = self.session_verify[account_id]
        session_ids_to_remove = {
            session["session_id"] 
            for session in sessions_to_clean 
            if "session_id" in session
        }

        # Cleanup images từ session_images dictionary
        for session_id in session_ids_to_remove:
            self.session_images.pop(session_id, None)
        
        #cleanup session
        self.session_verify.pop(account_id,None)




    async def broadcast_student_submission(self, quiz_id: int, submission_data: dict):
        """Broadcast submission với thông tin progress"""
        message = {
            "type": "student_submission",
            "quiz_id": quiz_id,
            "student_mssv": submission_data["student_mssv"],
            "score": submission_data["score"],
            "submitted_count": submission_data["submitted_count"],
            "total_participants": submission_data["total_participants"],
            "timestamp": datetime.now().timestamp()
        }
        
        participants = self.room_participants.get(quiz_id, set())
        for mssv in participants:
            if mssv in self.active_connections:
                try:
                    await self.active_connections[mssv].send_text(json.dumps(message))
                except Exception as e:
                    print(f"❌ Failed to send submission to {mssv}: {e}")

    # === QUIZ STATUS CHECK FEATURES === 

    def is_quiz_active(self, quiz_id: int) -> dict:
        """Kiểm tra trạng thái quiz đang active hay không"""
        if quiz_id not in self.quiz_sessions:
            return {"active": False, "status": "not_found"}
        
        session = self.quiz_sessions[quiz_id]
        
        # Tính toán remaining time nếu quiz đang chạy
        if session["status"] == "active":
            elapsed = datetime.now().timestamp() - session["start_time"]
            remaining_time = max(0, session["duration"] - elapsed)
            remaining_seconds = int(remaining_time)
            # Nếu hết thời gian thì auto end quiz
            if remaining_time <= 0:
                asyncio.create_task(self.end_quiz(quiz_id))
                return {"active": False, "status": "expired"}
        else:
            remaining_time = session.get("remaining_time", 0)
        
        return {
            "active": True,
            "status": session["status"],
            "remaining_time": remaining_seconds,
            "teacher": session["teacher"],
            "original_duration": session.get("original_duration", 0)
        }
    
    async def send_quiz_status_response(self, mssv: str, quiz_id: int, status: dict):
        """Gửi quiz status response về frontend"""
        message = {
            "type": "quiz_status_response",
            "quiz_id": quiz_id,
            "data": status,
            "timestamp": datetime.now().timestamp()
        }
        
        await self.broadcast_to_all(message)
        # if mssv in self.active_connections:
        #     try:
        #         await self.active_connections[mssv].send_text(json.dumps(message))
        #         print(f"📤 Quiz status sent to {mssv}: Quiz {quiz_id} - {status.get('status', 'unknown')}")
        #     except Exception as e:
        #         print(f"❌ Failed to send quiz status to {mssv}: {e}")

    # === MESSAGE ROUTING ===
    
    async def handle_message(self, mssv: str, message: dict):
        """Centralized message routing dựa trên message type"""
        message_type = message.get("type")
        
        try:
            if message_type == "join_room":
                room_id = message.get("room_id")
                if room_id:
                    await self.join_room(mssv, room_id)
                    
            elif message_type == "leave_room":
                room_id = message.get("room_id")
                if room_id:
                    await self.leave_room(mssv, room_id)
            
            elif message_type == "check_quiz_status":
                # Frontend request để check quiz có active không
                quiz_id = message.get("quiz_id")
                if quiz_id:
                    status = self.is_quiz_active(quiz_id)
                    await self.send_quiz_status_response(mssv, quiz_id, status)
                    
            elif message_type == "quiz_control":
                await self.handle_quiz_control(mssv, message)
            
            elif message_type == "student_submit":
                quiz_id = message.get("quiz_id")
                score = message.get("score", 0)
                
                if quiz_id:
                    await self.handle_student_submit(mssv, quiz_id, score)

            elif message_type == "request_image":
                session_id = message.get("session_id")
                if session_id:
                    await self.send_session_image(mssv, session_id)

            elif message_type == "ping":
                await self.send_pong(mssv)
                
            else:
                print(f"⚠️ Unhandled message type from {mssv}: {message_type}")
                
        except Exception as e:
            print(f"❌ Message handling error for {mssv}: {e}")

    async def send_pong(self, mssv: str):
        """Gửi pong response"""
        if mssv in self.active_connections:
            try:
                await self.active_connections[mssv].send_text(json.dumps({"type": "pong"}))
            except Exception as e:
                print(f"❌ Failed to send pong to {mssv}: {e}")
                await self.disconnect(mssv)

    async def send_heartbeat(self, mssv: str):
        """Gửi heartbeat để maintain connection"""
        if mssv in self.active_connections:
            try:
                await self.active_connections[mssv].send_text(json.dumps({"type": "heartbeat"}))
            except Exception as e:
                print(f"❌ Failed to send heartbeat to {mssv}: {e}")
                await self.disconnect(mssv)

# Global manager instance
manager = ConnectionManager()