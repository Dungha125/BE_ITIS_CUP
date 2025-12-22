# Quick Start - Chạy API

## 1. Chạy Server

```bash
cd python-backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy tại: **http://localhost:8000**

## 2. Test API

### Option 1: Dùng Browser
- **Health Check**: http://localhost:8000/health
- **API Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Option 2: Dùng Script Test
```bash
# Cài requests nếu chưa có
pip install requests

# Chạy test script
python test_api.py
```

### Option 3: Dùng curl

```bash
# Health check
curl http://localhost:8000/health

# Get teams
curl http://localhost:8000/api/tournament/teams

# Register team
curl -X POST http://localhost:8000/api/tournament/register \
  -F "email=test@example.com" \
  -F "team_name=Đội Test" \
  -F "leader_name=Nguyễn Văn A" \
  -F "leader_student_id=SV123456" \
  -F "phone=0123456789" \
  -F "vice_leader_name=Trần Thị B" \
  -F "vice_leader_student_id=SV123457" \
  -F "vice_leader_phone=0987654321" \
  -F "members_list_text=Danh sách thành viên"
```

## 3. API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/health` | Health check |
| GET | `/api/tournament/teams` | Lấy danh sách đội |
| POST | `/api/tournament/register` | Đăng ký đội mới |
| POST | `/api/tournament/create-payment` | Tạo payment link MoMo |
| POST | `/api/tournament/momo-ipn` | IPN webhook từ MoMo |

## 4. Xem API Documentation

Sau khi chạy server, mở browser:
- **Swagger UI**: http://localhost:8000/docs
  - Xem tất cả endpoints
  - Test API trực tiếp trên browser
  - Xem request/response schemas

- **ReDoc**: http://localhost:8000/redoc
  - Documentation đẹp hơn
  - Dễ đọc hơn

## 5. Troubleshooting

### Server không chạy được
```bash
# Kiểm tra dependencies
pip install -r requirements.txt

# Kiểm tra database
# Đảm bảo đã chạy migration
alembic upgrade head
```

### Port 8000 đã được sử dụng
```bash
# Dùng port khác
uvicorn app.main:app --reload --port 8001
```

### Database error
- Kiểm tra file `.env` có DATABASE_URL đúng không
- Với SQLite: `DATABASE_URL=sqlite:///./tournament.db`
- Đảm bảo đã chạy migration: `alembic upgrade head`

