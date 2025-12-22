"""
Script để tạo tài khoản admin
Chạy: python create_admin.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User
from app.services.auth_service import AuthService

def create_admin():
    """Tạo tài khoản admin"""
    db = SessionLocal()
    try:
        # Thông tin admin mặc định
        admin_username = "admin"
        admin_email = "admin@itiscup.com"
        admin_password = "admin123"  # Đổi mật khẩu sau khi tạo
        admin_full_name = "Administrator"
        
        # Kiểm tra xem đã có admin chưa
        existing_admin = db.query(User).filter(
            (User.username == admin_username) | (User.email == admin_email)
        ).first()
        
        if existing_admin:
            print(f"⚠️  Tài khoản admin đã tồn tại!")
            print(f"   Username: {existing_admin.username}")
            print(f"   Email: {existing_admin.email}")
            print(f"   Is Admin: {existing_admin.is_admin}")
            
            # Nếu chưa phải admin, cập nhật
            if not existing_admin.is_admin:
                existing_admin.is_admin = True
                db.commit()
                print(f"✅ Đã cập nhật tài khoản thành admin!")
            return
        
        # Tạo admin mới
        hashed_password = AuthService.get_password_hash(admin_password)
        
        admin = User(
            full_name=admin_full_name,
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            is_active=True,
            is_admin=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Tạo tài khoản admin thành công!")
        print(f"   Username: {admin_username}")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"\n⚠️  LƯU Ý: Đổi mật khẩu ngay sau khi đăng nhập!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi tạo admin: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

