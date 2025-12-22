# Hướng Dẫn Tạo Tài Khoản Admin

## Cách tạo tài khoản admin

1. **Chạy migration để thêm field `is_admin` vào bảng `users`:**
   ```bash
   cd python-backend
   alembic upgrade head
   ```

2. **Chạy script để tạo tài khoản admin:**
   ```bash
   python create_admin.py
   ```

3. **Thông tin đăng nhập mặc định:**
   - Username: `admin`
   - Email: `admin@itiscup.com`
   - Password: `admin123`
   
   ⚠️ **LƯU Ý:** Đổi mật khẩu ngay sau khi đăng nhập!

## Truy cập trang quản lý

Sau khi đăng nhập với tài khoản admin, truy cập:
- URL: `/admin/tournament-teams`
- Chức năng: Xem danh sách tất cả các đội và xóa đội

## API Endpoints (Admin Only)

- `DELETE /api/tournament/teams/{team_id}` - Xóa một đội (chỉ admin)

