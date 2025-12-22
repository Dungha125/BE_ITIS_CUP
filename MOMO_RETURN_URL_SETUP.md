# Cấu Hình MoMo Return URL

## Vấn Đề

Sau khi thanh toán MoMo, user bị redirect về "bad page" thay vì quay lại trang đăng ký.

## Nguyên Nhân

`MOMO_RETURN_URL` trong `.env` chưa được cấu hình đúng hoặc không tồn tại route callback.

## Giải Pháp

### 1. Cấu Hình Return URL trong `.env`

Tạo/update file `.env` trong `python-backend/`:

```env
# Return URL - Trang mà MoMo redirect về sau khi thanh toán
# Development (localhost)
MOMO_RETURN_URL=http://localhost:3000/itiscup/payment/callback

# Production
# MOMO_RETURN_URL=https://yourdomain.com/itiscup/payment/callback
```

### 2. Đảm Bảo Route Callback Tồn Tại

Đã tạo route callback tại: `app/itiscup/payment/callback/page.tsx`

Route này sẽ:
- Nhận query params từ MoMo (`orderId`, `resultCode`, `message`)
- Hiển thị trạng thái thanh toán
- Redirect về `/itiscup?tab=dangky&payment=success`

### 3. Restart Backend

Sau khi cập nhật `.env`, **restart backend**:

```bash
# Dừng server (Ctrl+C)
# Chạy lại
cd python-backend
uvicorn app.main:app --reload
```

### 4. Test Flow

1. Đăng ký đội → Nhận order_id
2. Click "Thanh Toán" → Redirect đến MoMo
3. Thanh toán trên MoMo
4. MoMo redirect về `/itiscup/payment/callback?orderId=...&resultCode=0`
5. Callback page xử lý → Redirect về `/itiscup?tab=dangky&payment=success`
6. Trang đăng ký tự động refresh danh sách đội

## Lưu Ý

- Return URL phải là **public** (không thể dùng localhost trong production)
- Return URL có thể là HTTP (không nhất thiết HTTPS)
- IPN URL phải là HTTPS và public

