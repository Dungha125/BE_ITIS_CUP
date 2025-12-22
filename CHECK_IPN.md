# Hướng Dẫn Kiểm Tra IPN Webhook

## Vấn đề: IPN không được gọi

Nếu IPN không được gọi từ MoMo, hãy kiểm tra các bước sau:

## 1. Kiểm tra IPN URL trong MoMo Dashboard

1. Đăng nhập vào MoMo Business Dashboard
2. Vào phần **Cài đặt** hoặc **Webhook Configuration**
3. Kiểm tra IPN URL phải là:
   ```
   https://beitiscup-production.up.railway.app/api/tournament/momo-ipn
   ```
4. Đảm bảo:
   - URL phải là HTTPS (không phải HTTP)
   - Không có trailing slash (/)
   - URL phải accessible từ internet

## 2. Kiểm tra IPN URL trong Environment Variables

Trên Railway, kiểm tra biến môi trường:
- `MOMO_NOTIFY_URL` phải là: `https://beitiscup-production.up.railway.app/api/tournament/momo-ipn`

## 3. Test IPN Endpoint

### 3.1. Test endpoint accessibility

Truy cập URL sau trong browser hoặc curl:
```
GET https://beitiscup-production.up.railway.app/api/tournament/test-ipn
```

Nếu thấy response JSON với thông tin IPN URL, endpoint đang hoạt động.

### 3.2. Test IPN Endpoint Thủ Công

Có thể test IPN endpoint bằng cách gửi request thủ công:

```bash
curl -X POST https://beitiscup-production.up.railway.app/api/tournament/momo-ipn \
  -H "Content-Type: application/json" \
  -d '{
    "partnerCode": "MOMO7YYL20251222",
    "orderId": "TEST_ORDER",
    "amount": 1000,
    "resultCode": 0,
    "transId": "123456789",
    "signature": "test_signature"
  }'
```

Nếu endpoint trả về `204 No Content`, endpoint đang hoạt động.

## 4. Kiểm tra Logs trên Railway

Xem logs để kiểm tra:
1. IPN URL có được log khi tạo payment link không:
   ```
   Using IPN URL: https://...
   MoMo Request Body: {..., "ipnUrl": "https://..."}
   ```

2. IPN có được gọi không:
   ```
   ✅ MoMo IPN received: orderId=..., resultCode=...
   ```

## 5. Lưu ý về IPN

- MoMo có thể delay việc gọi IPN (có thể mất vài phút)
- IPN chỉ được gọi khi thanh toán thành công (resultCode = 0)
- Nếu IPN URL không accessible, MoMo sẽ không gọi
- MoMo yêu cầu response HTTP 204 trong vòng 15 giây

## 6. Nếu IPN vẫn không được gọi

1. Kiểm tra lại IPN URL trong MoMo dashboard
2. Đảm bảo Railway service đang chạy và accessible
3. Kiểm tra firewall/security settings trên Railway
4. Liên hệ MoMo support nếu cần

