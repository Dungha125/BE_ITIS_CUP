# Hướng Dẫn Reset Database trên Railway

## Vấn đề
Migration đang cố tạo lại table `users` và `teams` nhưng chúng đã tồn tại, gây lỗi `DuplicateTable`.

## Giải pháp

### Cách 1: Reset Database (Xóa tất cả và tạo lại)

1. **Chạy script reset database:**
   ```bash
   railway run python reset_database_railway.py
   ```

2. **Sau khi reset, chạy migration:**
   ```bash
   railway run alembic upgrade head
   ```

3. **Tạo admin user (hoặc app sẽ tự tạo khi restart):**
   ```bash
   railway run python create_admin.py
   ```

### Cách 2: Sửa migration để handle table đã tồn tại

Migration đã được sửa để check table đã tồn tại trước khi tạo. Chỉ cần chạy:

```bash
railway run alembic upgrade head
```

### Cách 3: Thêm column is_admin thủ công (nếu table đã tồn tại)

Nếu chỉ cần thêm column `is_admin` mà không muốn reset:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;
```

Sau đó chạy:
```bash
railway run alembic stamp head
```

## Thông tin Admin

Sau khi reset và migration:
- Username: `admin`
- Email: `admin@itiscup.com`
- Password: `admin123`

⚠️ **Đổi mật khẩu ngay sau khi đăng nhập!**

