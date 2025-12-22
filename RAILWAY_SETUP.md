# Hướng Dẫn Deploy Backend lên Railway

## Tổng Quan

Railway là platform để deploy ứng dụng nhanh chóng. Backend Python FastAPI sẽ được deploy lên Railway với PostgreSQL database.

## Bước 1: Chuẩn Bị

### 1.1. Tạo tài khoản Railway

1. Truy cập: https://railway.app
2. Đăng ký/Đăng nhập bằng GitHub
3. Tạo project mới

### 1.2. Cài Railway CLI (Optional)

```bash
# Windows (PowerShell)
iwr https://railway.app/install.ps1 | iex

# Mac/Linux
curl -fsSL https://railway.app/install.sh | sh
```

## Bước 2: Deploy Backend

### 2.1. Kết nối GitHub Repository

1. Trong Railway dashboard, click **"New Project"**
2. Chọn **"Deploy from GitHub repo"**
3. Chọn repository `itis_portfolio`
4. Chọn root directory: `python-backend`

### 2.2. Cấu Hình Build

Railway sẽ tự động detect Dockerfile và build. Nếu không:
- **Builder**: Dockerfile
- **Dockerfile Path**: `Dockerfile`
- **Root Directory**: `python-backend`

### 2.3. Tạo PostgreSQL Database

1. Trong Railway project, click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway sẽ tự động tạo PostgreSQL database
3. Copy **DATABASE_URL** từ database service

## Bước 3: Cấu Hình Environment Variables

Trong Railway project, vào **"Variables"** tab và thêm:

### 3.1. Database

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

Railway tự động inject DATABASE_URL từ PostgreSQL service.

### 3.2. JWT Secret Key

```env
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
```

Generate secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.3. MoMo Payment Gateway

```env
MOMO_API_URL=https://test-payment.momo.vn/v2/gateway/api/create
MOMO_PARTNER_CODE=your_partner_code
MOMO_ACCESS_KEY=your_access_key
MOMO_SECRET_KEY=your_secret_key
MOMO_PARTNER_NAME=ITISCUP Tournament
MOMO_STORE_ID=ITISCUP
MOMO_RETURN_URL=https://your-frontend-domain.com/itiscup/payment/callback
MOMO_NOTIFY_URL=https://your-railway-app.railway.app/api/tournament/momo-ipn
```

**Lưu ý**: 
- `MOMO_RETURN_URL`: URL của frontend (Next.js)
- `MOMO_NOTIFY_URL`: URL của backend trên Railway (sẽ có dạng `https://xxx.railway.app`)

### 3.4. Port (Railway tự động set)

```env
PORT=8000
```

Railway tự động set PORT, không cần config.

## Bước 4: Deploy

### 4.1. Tự Động Deploy

Railway sẽ tự động deploy khi:
- Push code lên GitHub
- Thay đổi environment variables
- Manual trigger từ dashboard

### 4.2. Kiểm Tra Logs

1. Vào **"Deployments"** tab
2. Click vào deployment mới nhất
3. Xem logs để kiểm tra:
   - Build thành công
   - Database migration chạy
   - Server start

### 4.3. Kiểm Tra Health

1. Railway sẽ tự động tạo domain: `https://xxx.railway.app`
2. Test: `https://xxx.railway.app/health`
3. Nên trả về: `{"status": "healthy"}`

## Bước 5: Custom Domain (Optional)

1. Vào **"Settings"** → **"Networking"**
2. Click **"Generate Domain"** hoặc **"Custom Domain"**
3. Cấu hình DNS nếu dùng custom domain

## Bước 6: Cập Nhật Frontend

Cập nhật `config/tournamentApi.js`:

```javascript
BASE_URL: process.env.NEXT_PUBLIC_TOURNAMENT_API_URL || 'https://your-railway-app.railway.app/api',
```

Hoặc tạo `.env.local`:

```env
NEXT_PUBLIC_TOURNAMENT_API_URL=https://your-railway-app.railway.app/api
```

## Troubleshooting

### Lỗi: Database connection failed

- Kiểm tra DATABASE_URL có đúng không
- Đảm bảo PostgreSQL service đã được tạo
- Kiểm tra network settings trong Railway

### Lỗi: Migration failed

- Kiểm tra logs trong Railway
- Đảm bảo database đã được tạo
- Chạy migration thủ công nếu cần:
  ```bash
  railway run alembic upgrade head
  ```

### Lỗi: Port already in use

- Railway tự động set PORT, không cần config
- Kiểm tra CMD trong Dockerfile

### Lỗi: Module not found

- Kiểm tra requirements.txt có đầy đủ dependencies
- Rebuild deployment

## Monitoring

Railway cung cấp:
- **Metrics**: CPU, Memory, Network
- **Logs**: Real-time logs
- **Deployments**: Lịch sử deployments

## Cost

- Railway có free tier: $5 credit/tháng
- PostgreSQL: ~$5/tháng
- Tính toán dựa trên usage

## Backup

1. Railway tự động backup PostgreSQL
2. Có thể export database:
   ```bash
   railway connect postgres
   pg_dump > backup.sql
   ```

## Next Steps

1. ✅ Deploy backend lên Railway
2. ✅ Cấu hình environment variables
3. ✅ Test API endpoints
4. ✅ Cập nhật frontend để dùng Railway URL
5. ✅ Setup custom domain (optional)
6. ✅ Monitor và optimize

