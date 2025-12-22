# Cấu Hình MoMo Payment Gateway

## Vấn Đề: "Mã momo quét không hợp lệ" hoặc "Bad page" sau khi thanh toán

## Nguyên Nhân

1. **Return URL không đúng**: MoMo redirect về URL không tồn tại
2. **QR Code URL không hợp lệ**: Có thể do cấu hình MoMo credentials sai
3. **IPN URL không public**: MoMo không thể gọi được webhook

## Giải Pháp

### 1. Cấu Hình Return URL

Return URL là trang mà MoMo sẽ redirect về sau khi thanh toán.

**Cấu hình trong `.env`**:
```env
MOMO_RETURN_URL=http://localhost:3000/itiscup/payment/callback
# Hoặc production:
# MOMO_RETURN_URL=https://yourdomain.com/itiscup/payment/callback
```

### 2. Cấu Hình IPN URL

IPN URL là webhook mà MoMo gọi để thông báo kết quả thanh toán.

**Cấu hình trong `.env`**:
```env
MOMO_NOTIFY_URL=http://localhost:8000/api/tournament/momo-ipn
# Hoặc production (PHẢI là HTTPS và public):
# MOMO_NOTIFY_URL=https://yourdomain.com/api/tournament/momo-ipn
```

**Lưu ý**: IPN URL phải là **HTTPS** và **public** (MoMo không gọi được localhost)

### 3. Test với Ngrok (Development)

Nếu test local, dùng ngrok để expose backend:

```bash
# Cài ngrok
# https://ngrok.com/

# Expose backend port 8000
ngrok http 8000

# Sẽ có URL như: https://abc123.ngrok.io
# Cập nhật .env:
MOMO_NOTIFY_URL=https://abc123.ngrok.io/api/tournament/momo-ipn
MOMO_RETURN_URL=http://localhost:3000/itiscup/payment/callback
```

### 4. Kiểm Tra MoMo Credentials

Đảm bảo các thông tin sau đúng:

```env
MOMO_PARTNER_CODE=your_partner_code
MOMO_ACCESS_KEY=your_access_key
MOMO_SECRET_KEY=your_secret_key
```

### 5. Kiểm Tra API URL

- **Sandbox**: `https://test-payment.momo.vn/v2/gateway/api/create`
- **Production**: `https://payment.momo.vn/v2/gateway/api/create`

```env
MOMO_API_URL=https://test-payment.momo.vn/v2/gateway/api/create
```

## Flow Thanh Toán

1. User click "Thanh Toán" → Gọi `/api/tournament/create-payment`
2. Backend tạo payment link từ MoMo → Trả về `payUrl`
3. Frontend redirect đến `payUrl` (trang thanh toán MoMo)
4. User thanh toán trên MoMo
5. MoMo redirect về `MOMO_RETURN_URL` với query params:
   - `orderId`: Mã đơn hàng
   - `resultCode`: 0 = thành công, khác 0 = thất bại
   - `message`: Thông báo
6. Frontend xử lý callback → Redirect về `/itiscup?tab=dangky&payment=success`
7. MoMo gọi IPN webhook đến `MOMO_NOTIFY_URL` → Backend xử lý và cập nhật status

## Troubleshooting

### Lỗi: "Mã momo quét không hợp lệ"
- Kiểm tra MoMo credentials (Partner Code, Access Key, Secret Key)
- Kiểm tra API URL (sandbox vs production)
- Kiểm tra signature có đúng không

### Lỗi: "Bad page" sau khi thanh toán
- Kiểm tra `MOMO_RETURN_URL` có đúng không
- Đảm bảo route `/itiscup/payment/callback` tồn tại
- Kiểm tra frontend có xử lý callback đúng không

### IPN không được gọi
- IPN URL phải là HTTPS và public
- Dùng ngrok để test local
- Kiểm tra firewall/security settings

## Test

1. Đăng ký đội → Nhận order_id
2. Tạo payment link → Nhận payUrl
3. Mở payUrl → Thanh toán trên MoMo (sandbox)
4. Kiểm tra redirect về callback page
5. Kiểm tra IPN webhook được gọi
6. Kiểm tra status team được cập nhật

