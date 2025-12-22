# Hướng Dẫn Setup Database

## Option 1: SQLite (Khuyến nghị cho Development)

SQLite không cần cài đặt database server, rất dễ dàng cho development.

### Bước 1: Tạo file `.env`
```bash
cp .env.example .env
```

File `.env` sẽ có:
```env
DATABASE_URL=sqlite:///./tournament.db
```

### Bước 2: Chạy migration
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

Database file `tournament.db` sẽ được tạo tự động trong thư mục `python-backend/`.

## Option 2: PostgreSQL (Cho Production)

### Bước 1: Cài đặt PostgreSQL
- Download và cài đặt từ: https://www.postgresql.org/download/
- Hoặc dùng Docker: `docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres`

### Bước 2: Tạo database
```sql
CREATE DATABASE tournament_db;
CREATE USER tournament_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE tournament_db TO tournament_user;
```

### Bước 3: Cấu hình `.env`
```env
DATABASE_URL=postgresql://tournament_user:your_password@localhost:5432/tournament_db
```

### Bước 4: Chạy migration
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Option 3: MySQL (Cho Production)

### Bước 1: Cài đặt MySQL
- Download và cài đặt từ: https://dev.mysql.com/downloads/
- Hoặc dùng Docker: `docker run --name mysql -e MYSQL_ROOT_PASSWORD=password -e MYSQL_DATABASE=tournament_db -p 3306:3306 -d mysql`

### Bước 2: Cấu hình `.env`
```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/tournament_db
```

### Bước 3: Cài thêm package
```bash
pip install pymysql
```

### Bước 4: Chạy migration
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Troubleshooting

### Lỗi: "password authentication failed"
- Kiểm tra username và password trong `.env`
- Đảm bảo database đã được tạo
- Kiểm tra PostgreSQL/MySQL đang chạy

### Lỗi: "database does not exist"
- Tạo database trước khi chạy migration
- Kiểm tra tên database trong `.env`

### Lỗi: "connection refused"
- Kiểm tra database server đang chạy
- Kiểm tra port (PostgreSQL: 5432, MySQL: 3306)
- Kiểm tra firewall settings

## Khuyến nghị

- **Development**: Dùng SQLite (dễ setup, không cần server)
- **Production**: Dùng PostgreSQL hoặc MySQL (hiệu năng tốt hơn)

