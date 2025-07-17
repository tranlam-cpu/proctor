# Query để lấy quyền trong vai trò
GET_FEATURE_PERMISSION = """
    SELECT 
        cqv.chuc_nang_id as ten_chuc_nang,
        cqv.bitwise as ten_quyen
    FROM chucnang_quyen_vaitro cqv
    WHERE cqv.vai_tro_id = :vai_tro_id
    ORDER BY cqv.chuc_nang_id
"""

GET_PERSON_EMMBEDING ="""
    SELECT u.ma_so, u.ho_ten, u.email, COUNT(fe.id) as face_count
            FROM nguoidung u
            LEFT JOIN nhandien fe ON u.ma_so = fe.nguoi_dung_id
            GROUP BY u.ma_so, u.ho_ten, u.email
"""

