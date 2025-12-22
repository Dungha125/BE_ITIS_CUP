# Hệ Thống Authentication cho ITISCUP Tournament

## Tổng Quan

Hệ thống cho phép đại diện các đội đăng ký tài khoản để quản lý đội và thanh toán sau.

## Tính Năng

1. **Đăng ký tài khoản**: Họ và tên, username, password, email
2. **Đăng nhập**: JWT token authentication
3. **Quản lý đội**: Link đội với user để quản lý
4. **Thanh toán sau**: Không cần thanh toán ngay khi đăng ký

## API Endpoints

### 1. Đăng Ký Tài Khoản

```http
POST /api/auth/register
Content-Type: application/json

{
  "full_name": "Nguyễn Văn A",
  "username": "nguyenvana",
  "email": "nguyenvana@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Đăng ký thành công",
  "data": {
    "id": 1,
    "full_name": "Nguyễn Văn A",
    "username": "nguyenvana",
    "email": "nguyenvana@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

### 2. Đăng Nhập

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "nguyenvana",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Đăng nhập thành công",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "full_name": "Nguyễn Văn A",
      "username": "nguyenvana",
      "email": "nguyenvana@example.com",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  }
}
```

### 3. Lấy Thông Tin User Hiện Tại

```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": 1,
  "full_name": "Nguyễn Văn A",
  "username": "nguyenvana",
  "email": "nguyenvana@example.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## Đăng Ký Đội với Authentication

### Có Đăng Nhập (Recommended)

1. User đăng nhập → Nhận access_token
2. Đăng ký đội với header: `Authorization: Bearer {access_token}`
3. Đội sẽ được link với user
4. User có thể quản lý các đội của mình

### Không Đăng Nhập

- Vẫn có thể đăng ký đội bình thường
- Đội không được link với user nào
- Không thể quản lý sau này

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Teams Table (Updated)

```sql
ALTER TABLE teams ADD COLUMN user_id INTEGER REFERENCES users(id);
```

## Security

- Password được hash bằng bcrypt
- JWT token với expiration 7 days
- Token được verify trong mỗi request
- CORS được cấu hình trong main.py

## Environment Variables

```env
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
```

Generate secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

