import logging
from sqlalchemy import text
from app.models.base import Taikhoan, Nguoidung, Vaitro, ChucnangQuyenVaitro
from app.core.security import get_password_hash
from app.db.base import db_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database() -> None:
    """
    Khởi tạo database và tạo admin user 
    """
    try:
        with db_handler.get_session("mysql") as db:
            # Kiểm tra admin user đã tồn tại chưa
            existing_user = db.query(Taikhoan).filter(
                Taikhoan.nguoi_dung_id == "root"
            ).first()
            

            # Kiểm tra và Tạo vai trò mặc định (admin, sinh viên, giáo viên)
            existing_vaitro_admin = db.query(Vaitro).filter(
                Vaitro.ten_vai_tro == "admin"
            ).first()

            existing_vaitro_sinhvien = db.query(Vaitro).filter(
                Vaitro.ten_vai_tro == "sinh viên"
            ).first()

            existing_vaitro_giaovien = db.query(Vaitro).filter(
                Vaitro.ten_vai_tro == "giáo viên"
            ).first()
            
            if not existing_vaitro_giaovien:
                logger.info("Tạo vai trò giáo viên mới...")

                try:
                    vaitro_giaovien = Vaitro(
                        id = 3,
                        ten_vai_tro = 'giáo viên'
                    )
                    db.add(vaitro_giaovien)
                    
                    # Commit thay vì dùng context manager
                    db.commit()
                    
                    logger.info("✅ Giáo viên role đã được tạo thành công")
                    
                except Exception as e:
                    # Rollback cho các lỗi khác
                    db.rollback()
                    logger.error(f"❌ Lỗi tạo: {e}")
                    raise

            if not existing_vaitro_sinhvien:
                logger.info("Tạo vai trò sinh viên mới...")

                try:
                    vaitro_sinhvien = Vaitro(
                        id = 2,
                        ten_vai_tro = 'sinh viên'
                    )
                    db.add(vaitro_sinhvien)
                    
                    # Commit thay vì dùng context manager
                    db.commit()
                    
                    logger.info("✅ Sinh viên role đã được tạo thành công")
                    
                except Exception as e:
                    # Rollback cho các lỗi khác
                    db.rollback()
                    logger.error(f"❌ Lỗi tạo {e}")
                    raise

            if not existing_vaitro_admin:
                logger.info("Tạo vai trò admin mới...")

                try:
                    vaitro_admin = Vaitro(
                        id = 1,
                        ten_vai_tro = 'admin'
                    )
                    db.add(vaitro_admin)
                    
                    # Commit thay vì dùng context manager
                    db.commit()
                    
                    logger.info("✅ Admin role đã được tạo thành công")
                except Exception as e:
                    # Rollback cho các lỗi khác
                    db.rollback()
                    logger.error(f"❌ Lỗi tạo {e}")
                    raise

            if not existing_user:
                logger.info("Tạo admin user mới...")
                
                try:
                    # Tạo Nguoidung trước
                    admin_per = Nguoidung(
                        ma_so="root",
                        ho_ten="System Administrator"
                    )
                    db.add(admin_per)
                    db.flush()  # Lấy ID ngay lập tức
                    
                    logger.info(f"Đã tạo Nguoidung với ma_so: {admin_per.ma_so}")                                   

                    # Tạo Taikhoan với foreign key
                    admin_user = Taikhoan(
                        nguoi_dung_id=admin_per.ma_so,
                        vai_tro_id= 1,
                        mat_khau=get_password_hash("Admin@123")
                    )
                    db.add(admin_user)
                    
                    # Set Quyền Default
                    permission = ChucnangQuyenVaitro(
                        chuc_nang_id="role",
                        bitwise= 15,
                        vai_tro_id= 1 
                    )
                    db.add(permission)
                    
                    # Commit thay vì dùng context manager
                    db.commit()
                    
                    logger.info("✅ Admin user đã được tạo thành công")
                    logger.info("👤 Username: root | 🔑 Password: Admin@123")
                    
                    
       
                except Exception as e:
                    # Rollback cho các lỗi khác
                    db.rollback()
                    logger.error(f"❌ Lỗi tạo admin user: {e}")
                    raise
                    
            else:
                logger.info("ℹ️  Admin user đã tồn tại, bỏ qua việc tạo mới")
            
            # Test kết nối database
            result = db.execute(text("SELECT 1 as test_connection"))
            test_value = result.scalar()
            logger.info(f"✅ Kiểm tra kết nối database: {test_value}")
            
    except Exception as e:
        logger.error(f"❌ Lỗi khởi tạo database: {e}")
        logger.error(f"🔍 Chi tiết lỗi: {type(e).__name__}")
        raise




if __name__ == "__main__":
    create_database()
