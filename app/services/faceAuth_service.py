from app.services.faceRecognition_service import FaceRecognitionSystem
from app.schemas.face import AuthStatusResponse
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
from deepface import DeepFace



class ContinuousAuthManager:
    def __init__(self):
        # Lưu trữ thông tin session và baseline
        self.user_sessions: Dict[int, Dict] = {}
        self.user_baselines: Dict[int, List[float]] = {}
        self.verification_schedule: Dict[int, Dict] = {}
        self.face_system = FaceRecognitionSystem()
    
    async def initialize_session(
        self, 
        account_id: int, 
        room_id: int, 
        baseline_image, 
        db
    ) -> Dict:
        """
        Khởi tạo session xác thực liên tục
        """
        try:
            # Tạo baseline encoding - đảm bảo user đúng danh tính
            baseline_result = self.face_system.authenticate_face(db, baseline_image)
            
            if not baseline_result.get("success"):
                return {
                    "success": False,
                    "message": baseline_result
                }
            
            # Lưu baseline và khởi tạo session
            #baselineEmbedding = self.face_system.extract_embedding(baseline_image)
            #self.user_baselines[account_id] = baselineEmbedding
            self.user_baselines[account_id] = baseline_image

            session_token = f"session_{account_id}_{datetime.utcnow().timestamp()}"

            self.user_sessions[account_id] = {
                "room_id": room_id,
                "start_time": datetime.utcnow(),
                "last_verification": datetime.utcnow(),
                "verification_count": 1,
                "fraud_score": 0.0,
                "status": "active",
                "session_token":session_token,
                "baseline_confidence": baseline_result.get("authentication_details", {}).get("svm_confidence", 0.0),
                "consecutive_failures": 0,
                "technical_failures": 0
            }
            
            # Thiết lập schedule verification đầu tiên
            self._update_verification_schedule(account_id, 0.0)
           
            return {
                "success": True,
                "session_token": session_token,
                "baseline_confidence": baseline_result.get("authentication_details", {}).get("final_score", 0.0),
                "initial_interval": 30  # 30 giây đầu tiên
            }
        except Exception as e:
            print(e)
            
    
    def get_verification_status(self, account_id: int) -> AuthStatusResponse:
        """
        Client polling endpoint - kiểm tra có cần verify không
        """
        if account_id not in self.user_sessions:
            return AuthStatusResponse(
                should_verify=False,
                session_token="no_session",
                verification_interval=0,
                fraud_score=0.0,
                status="no_session",
                message="No active session found",
                next_check_after=60
            )
        
        session = self.user_sessions[account_id]
        schedule = self.verification_schedule.get(account_id, {})
        
        current_time = datetime.utcnow()
        last_verification = session["last_verification"]
        time_since_last = (current_time - last_verification).total_seconds()
        
        required_interval = schedule.get("interval", 30)
        should_verify = time_since_last >= required_interval
        
        next_check = 0 if should_verify else int(required_interval - time_since_last)
        
        return AuthStatusResponse(
            should_verify=should_verify,
            session_token=session["session_token"],
            verification_interval=required_interval,
            fraud_score=session["fraud_score"],
            status=session["status"],
            message=f"Next verification in {next_check}s" if not should_verify else "Verification required",
            next_check_after=max(5, next_check)
        )

    async def process_verification(
        self, 
        account_id: int, 
        verification_image 
    ) -> Dict:
        """
        Xử lý ảnh verification từ client
        """
        if account_id not in self.user_sessions:
            return {
                "success": False,
                "message": "No active session"
            }
        
        if account_id not in self.user_baselines:
            return {
                "success": False,
                "message": "No baseline found for comparison",
            }

        #session = self.user_sessions[account_id]

        # try:
        #     current_embedding = self.face_system.extract_embedding(verification_image)
        # except Exception as e:
        #     return await self._handle_technical_failure(account_id, "embedding_extraction_failed")
        
        # if current_embedding is None:
        #     return await self._handle_technical_failure(account_id, "no_face_detected")

        if verification_image is None:
            return await self._handle_technical_failure(account_id, "no_face_detected")
        
        faces = FaceRecognitionSystem().detect_faces(verification_image)

         # không detect được khuôn mặt
        if len(faces) == 0:
            return await self._handle_technical_failure(account_id, "similarity_calculation_failed")
        
        # # 2 người được nhận diện
        if len(faces) > 1:
            return await self._handle_verification_failure(account_id, "high_similarity")
        
        baseline_embedding = self.user_baselines[account_id]
        try:
            #similarity_score = self.face_system.calculate_similarity(baseline_embedding, current_embedding)
            # Số càng nhỏ càng giống
            similarity_score = DeepFace.verify(img1_path = baseline_embedding, img2_path = verification_image,model_name="VGG-Face")['distance']
        
            # Phân tích kết quả verification
            verification_result  = await self._analyze_verification_result(account_id, similarity_score)
            
            if verification_result["success"]:
                await self._handle_successful_verification(account_id, similarity_score)
            else:
                await self._handle_verification_failure(account_id, verification_result["reason"])
            
            return verification_result
        
        except Exception as e:
            similarity_score: float = 1.0
            verification_result  = await self._analyze_verification_result(account_id, similarity_score)
            # return await self._handle_technical_failure(account_id, "similarity_calculation_failed")
            return await self._handle_verification_failure(account_id, verification_result["reason"])


        
    # async def _analyze_verification_result(self, account_id: int, similarity_score: float) -> Dict:
    #     """
    #     Phân tích kết quả verification dựa trên similarity score
    #     """
    #     session = self.user_sessions[account_id]

    #     base_threshold = 0.75
    #     # adjusted_threshold = base_threshold + (session["fraud_score"] * 0.1)  # Tăng threshold khi có risk
    #     adjusted_threshold = min(0.85, base_threshold + (session["fraud_score"] * 0.1))
    #     if similarity_score >= adjusted_threshold:
    #         # Verification thành công
    #         fraud_score = max(0.0, session["fraud_score"] - 0.1)  # Giảm fraud score khi pass
    #         return {
    #             "success": True,
    #             "similarity_score": similarity_score,
    #             "threshold_used": adjusted_threshold,
    #             "fraud_score": fraud_score,
    #             "status": "verified",
    #             "message": f"Verification successful (similarity: {similarity_score:.3f})"
    #         }
        
    #     elif similarity_score >= 0.6:
    #         # Suspicious - có thể là góc chụp, ánh sáng khác
    #         fraud_score = min(1.0, session["fraud_score"] + 0.2)
    #         return {
    #             "success": False,
    #             "similarity_score": similarity_score,
    #             "threshold_used": adjusted_threshold,
    #             "fraud_score": fraud_score,
    #             "status": "suspicious",
    #             "reason": "moderate_similarity",
    #             "message": f"Suspicious verification (similarity: {similarity_score:.3f})"
    #         }
        
    #     else:
    #         # Possible fraud - similarity quá thấp
    #         fraud_score = min(1.0, session["fraud_score"] + 0.5)
    #         return {
    #             "success": False,
    #             "similarity_score": similarity_score,
    #             "threshold_used": adjusted_threshold,
    #             "fraud_score": fraud_score,
    #             "status": "fraud_detected",
    #             "reason": "low_similarity",
    #             "message": f"Potential fraud detected (similarity: {similarity_score:.3f})"
    #         }
    async def _analyze_verification_result(self, account_id: int, distance: float) -> Dict:
        """
        Phân tích kết quả verification dựa trên distance (càng nhỏ càng giống)
        """

        if account_id not in self.user_sessions:
            raise ValueError(f"No session found for account_id: {account_id}")
        
        session = self.user_sessions[account_id]
        
        # Threshold cho distance (càng nhỏ càng strict)
        base_threshold = 0.4  # DeepFace default threshold
        adjusted_threshold = max(0.3, base_threshold - (session["fraud_score"] * 0.1))
        
        if distance <= adjusted_threshold:
            # Verification thành công
            fraud_score = max(0.0, session["fraud_score"] - 0.1)
            return {
                "success": True,
                "distance": distance,
                "threshold_used": adjusted_threshold,
                "fraud_score": fraud_score,
                "status": "verified",
                "message": f"Verification successful (distance: {distance:.3f})"
            }
        
        elif distance <= 0.6:
            # Nghi ngờ
            fraud_score = min(1.0, session["fraud_score"] + 0.2)
            return {
                "success": False,
                "distance": distance,
                "threshold_used": adjusted_threshold,
                "fraud_score": fraud_score,
                "status": "suspicious",
                "reason": "moderate_similarity",
                "message": f"Suspicious verification (distance: {distance:.3f})"
            }
        
        else:
            # Fraud
            fraud_score = min(1.0, session["fraud_score"] + 0.5)
            return {
                "success": False,
                "distance": distance,
                "threshold_used": adjusted_threshold,
                "fraud_score": fraud_score,
                "status": "fraud_detected",
                "reason": "low_similarity",
                "message": f"Potential fraud detected (distance: {distance:.3f})"
            }
    
    async def _handle_successful_verification(self, account_id: int, similarity_score: float):
        """
        Xử lý khi verification thành công
        """
        session = self.user_sessions[account_id]
        
        # Reset các counters
        session["consecutive_failures"] = 0
        session["technical_failures"] = max(0, session["technical_failures"] - 1)
        
        # Cập nhật session info
        session["last_verification"] = datetime.utcnow()
        session["verification_count"] += 1
        session["fraud_score"] = max(0.0, session["fraud_score"] - 0.1)  # Reward good behavior
        session["status"] = "verified"
        
        # Cập nhật verification schedule
        self._update_verification_schedule(account_id, session["fraud_score"])

        return {
            "success": True,
        }
        
    
    async def _handle_verification_failure(self, account_id: int, reason: str):
        """
        Xử lý khi verification thất bại (potential fraud)
        """
        session = self.user_sessions[account_id]
        
        # Tăng consecutive failures
        session["consecutive_failures"] += 1
        
        # Penalty dựa trên severity
        penalty_map = {
            "low_similarity": 0.5,      # Nghiêm trọng - có thể person swapping
            "moderate_similarity": 0.2,  # Trung bình - có thể technical issue
        }
       
        penalty = penalty_map.get(reason, 0.3)
        session["fraud_score"] = min(1.0, session["fraud_score"] + penalty)
        
        # Cập nhật session
        session["last_verification"] = datetime.utcnow()
        session["verification_count"] += 1
        session["status"] = "fraud_suspected" if session["fraud_score"] > 0.7 else "verification_failed"
        # Cập nhật schedule với enhanced monitoring
        self._update_verification_schedule(account_id, session["fraud_score"])
        
        return {
            "success": False,
            "fraud_score": session["fraud_score"],
            "status": "verification_failure",
            "error_type": "verification",
            "action_required": "retry_with_better_conditions"
        }
       

    async def _handle_technical_failure(self, account_id: int, reason: str) -> Dict:
        """
        Xử lý technical failures - KHÔNG penalty fraud_score
        """
        session = self.user_sessions[account_id]
        session["technical_failures"] += 1
        
        # Chỉ tăng fraud score nếu quá nhiều technical failures (có thể cố tình)
        if session["technical_failures"] > 5:
            session["fraud_score"] = min(1.0, session["fraud_score"] + 0.1)
            message = f"Too many technical failures ({reason}). Please check your setup."
        else:
            message = f"Technical issue: {reason}. Please try again with better conditions."
        
        # Cập nhật verification schedule
        self._update_verification_schedule(account_id, session["fraud_score"])
        
        return {
            "success": False,
            "message": message,
            "fraud_score": session["fraud_score"],
            "status": "technical_failure",
            "error_type": "technical",
            "technical_failures_count": session["technical_failures"],
            "action_required": "retry_with_better_conditions"
        }
    
    def _update_verification_schedule(self, account_id: int, fraud_score: float):
        """
        Cập nhật verification schedule dựa trên fraud score
        """
        # Adaptive interval với enhanced monitoring khi có risk
        if fraud_score >= 0.8:
            interval = 10  # Verify mỗi 10s - high risk
        elif fraud_score >= 0.6:
            interval = 15  # Verify mỗi 15s - medium-high risk
        elif fraud_score >= 0.4:
            interval = 25  # Verify mỗi 25s - medium risk
        elif fraud_score >= 0.2:
            interval = 40  # Verify mỗi 40s - low risk
        else:
            interval = 60  # Verify mỗi 60s - clean
        
        self.verification_schedule[account_id] = {
            "interval": interval,
            "last_update": datetime.utcnow(),
            "risk_level": self._get_risk_level(fraud_score),
            "fraud_score": fraud_score
        }
    
    def _get_risk_level(self, fraud_score: float) -> str:
        """Xác định risk level dựa trên fraud score"""
        if fraud_score >= 0.8:
            return "critical"
        elif fraud_score >= 0.6:
            return "high"
        elif fraud_score >= 0.4:
            return "medium"
        elif fraud_score >= 0.2:
            return "low"
        else:
            return "clean"
        
    def end_session(self, account_id: int) -> Dict:
        """
        Kết thúc continuous authentication session
        """
        if account_id not in self.user_sessions:
            return {"success": False, "message": "No active session found"}
        
        session = self.user_sessions[account_id]
        
        # Tạo session report
        session_duration = (datetime.utcnow() - session["start_time"]).total_seconds()
        session_report = {
            "account_id": account_id,
            "duration_seconds": session_duration,
            "total_verifications": session["verification_count"],
            "final_fraud_score": session["fraud_score"],
            "final_status": session["status"],
            "technical_failures": session["technical_failures"],
            "consecutive_failures": session["consecutive_failures"]
        }
        
        # Cleanup session data
        del self.user_sessions[account_id]
        if account_id in self.user_baselines:
            del self.user_baselines[account_id]
        if account_id in self.verification_schedule:
            del self.verification_schedule[account_id]
        
        
        return {
            "success": True,
            "message": "Session ended successfully",
            "session_report": session_report
        }