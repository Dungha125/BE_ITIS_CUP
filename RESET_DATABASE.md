# Hướng dẫn Reset Database

## Cách 1: Sử dụng script (Khuyến nghị)

1. **Dừng server FastAPI** (nếu đang chạy):
   - Nhấn `Ctrl+C` trong terminal đang chạy server

2. **Chạy script reset**:
   ```bash
   cd python-backend
   python reset_db.py
   ```

3. **Khởi động lại server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Cách 2: Xóa thủ công

1. **Dừng server FastAPI**

2. **Xóa file database**:
   ```bash
   cd python-backend
   del tournament.db  # Windows
   # hoặc
   rm tournament.db    # Linux/Mac
   ```

3. **Tạo lại database**:
   ```bash
   python -m alembic upgrade head
   ```

4. **Khởi động lại server**

## Lưu ý

- **Phải dừng server trước khi reset database**, nếu không sẽ bị lỗi "file is being used by another process"
- Sau khi reset, tất cả dữ liệu (teams, users) sẽ bị xóa
- Database sẽ được tạo lại với schema mới nhất

