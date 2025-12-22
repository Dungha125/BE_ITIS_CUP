# Python Backend - Tournament Registration System (FastAPI)

## Cài Đặt

### 1. Tạo virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Cấu hình môi trường
Copy file `.env.example` thành `.env` và cấu hình:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/tournament_db
MOMO_API_URL=https://test-payment.momo.vn/v2/gateway/api/create
MOMO_PARTNER_CODE=your_partner_code
MOMO_ACCESS_KEY=your_access_key
MOMO_SECRET_KEY=your_secret_key
MOMO_RETURN_URL=https://yourdomain.com/tournament/payment/return
MOMO_NOTIFY_URL=https://yourdomain.com/api/tournament/momo-ipn
```

### 4. Chạy migration
```bash
# Tạo migration đầu tiên
alembic revision --autogenerate -m "Initial migration"

# Chạy migration
alembic upgrade head
```

### 5. Chạy server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### 1. Đăng ký đội
```
POST /api/tournament/register
Content-Type: multipart/form-data
```

### 2. Tạo payment link MoMo
```
POST /api/tournament/create-payment
```

### 3. IPN webhook từ MoMo
```
POST /api/tournament/momo-ipn
```

### 4. Lấy danh sách đội
```
GET /api/tournament/teams
```

## API Documentation

Sau khi chạy server, truy cập:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Cấu Trúc Code

```
python-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── database.py          # Database configuration
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   └── tournament.py    # Tournament routes
│   └── services/
│       ├── __init__.py
│       └── momo_service.py  # MoMo Payment service
├── alembic/                 # Database migrations
├── requirements.txt
├── .env.example
└── README.md
```

## Lưu Ý

1. IPN URL phải là HTTPS và public (MoMo không gọi được localhost)
2. Sử dụng ngrok hoặc similar tool để test IPN locally
3. Luôn verify signature từ MoMo IPN
4. Xử lý race condition với SELECT FOR UPDATE trong transaction
5. File upload được lưu trong `storage/teams/members/`

## So Sánh với Framework Khác

| Framework | FastAPI |
|---------|---------|
| Migration | Alembic |
| Eloquent Model | SQLAlchemy Model |
| Controller | Router |
| Service | Service (giữ nguyên) |
| Validation | Pydantic |
| Request/Response | Pydantic schemas |

