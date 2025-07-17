from typing import Dict, Set

class VerificationTracker:
    def __init__(self):
        # Lưu trữ các combination đã gọi: {account_id: set(fraud_scores)}
        self.called_combinations: Dict[str, Set[float]] = {}
    
    def should_allow_call(self, account_id: str, fraud_score: float) -> bool:
        """
        Kiểm tra có cho phép gọi API dựa trên account_id và fraud_score
        """
        # Khởi tạo set fraud_scores cho account nếu chưa có
        if account_id not in self.called_combinations:
            self.called_combinations[account_id] = set()
        
        # Kiểm tra xem combination này đã được gọi chưa
        if fraud_score in self.called_combinations[account_id]:
            return False  # Đã gọi rồi, không cho phép gọi lại
        
        # Ghi nhận combination này
        self.called_combinations[account_id].add(fraud_score)
        return True
    
    def reset_account(self, account_id: str):
        """
        Reset lại history cho một account cụ thể
        """
        if account_id in self.called_combinations:
            del self.called_combinations[account_id]
    
    def clear_all(self):
        """
        Xóa toàn bộ history
        """
        self.called_combinations.clear()
        
global_verification_tracker = VerificationTracker()