# Hướng Dẫn Deploy Payment Verification Feature

## Tổng Quan

Feature này thêm khả năng tự động xác thực trạng thái thanh toán MoMo bằng cách query trực tiếp API của MoMo, thay vì chỉ dựa vào IPN webhook.

### Lý do cần feature này:
- IPN webhook từ MoMo đôi khi không được gọi (network issues, firewall, etc.)
- User cần cách để xác nhận thanh toán đã thành công ngay lập tức
- Giảm phụ thuộc vào IPN webhook một chiều

## Các Thay Đổi

### 1. Database Migration

Thêm column `request_id` vào table `teams`:
- Column: `request_id` (String, nullable, indexed)
- Mục đích: Lưu request_id từ MoMo để query transaction status sau này

### 2. API Endpoints Mới

#### POST `/api/tournament/verify-payment/{order_id}`
- Xác thực trạng thái thanh toán chủ động
- Query MoMo API để kiểm tra transaction status
- Tự động cập nhật team status nếu payment thành công

#### GET `/api/tournament/team-status/{order_id}` (Updated)
- Tự động query MoMo nếu team chưa thanh toán
- Cập nhật status realtime
- Frontend chỉ cần poll endpoint này, không cần endpoint riêng

### 3. Service Updates

**MomoService** - Thêm method mới:
- `query_transaction(order_id, request_id)`: Query transaction status từ MoMo

## Deployment Steps

### Bước 1: Push Code lên Repository

```bash
git add .
git commit -m "Add payment verification feature with MoMo query API"
git push origin main
```

### Bước 2: Railway sẽ tự động deploy

Railway sẽ:
1. Pull code mới
2. Build Docker image
3. Deploy service mới

### Bước 3: Chạy Migration trên Railway

Sau khi deploy xong, chạy migration:

#### Option A: Sử dụng Railway CLI

```bash
# Install Railway CLI nếu chưa có
npm install -g @railway/cli

# Login
railway login

# Link với project
railway link

# Chạy migration
railway run python -m alembic upgrade head
```

#### Option B: Sử dụng Railway Dashboard

1. Vào Railway Dashboard
2. Chọn project `beitiscup-production`
3. Vào tab "Settings" → "Deployments"
4. Click "Deploy" → "Run Command"
5. Nhập command: `python -m alembic upgrade head`

#### Option C: Temporary Shell (Khuyến nghị)

1. SSH vào Railway service:
```bash
railway connect
```

2. Chạy migration:
```bash
cd python-backend
python -m alembic upgrade head
```

3. Kiểm tra migration đã chạy thành công:
```bash
python -m alembic current
```

Bạn sẽ thấy:
```
fbe4bf76bbd3 (head)
```

### Bước 4: Verify Environment Variables

Đảm bảo các biến môi trường sau đã được set trên Railway:

```env
MOMO_API_URL=https://test-payment.momo.vn/v2/gateway/api/create
MOMO_QUERY_URL=https://test-payment.momo.vn/v2/gateway/api/query
MOMO_PARTNER_CODE=...
MOMO_ACCESS_KEY=...
MOMO_SECRET_KEY=...
MOMO_NOTIFY_URL=https://beitiscup-production.up.railway.app/api/tournament/momo-ipn
MOMO_RETURN_URL=https://your-frontend-url.com/itiscup/payment/callback
```

**LƯU Ý**: `MOMO_QUERY_URL` mới được thêm. Nếu không set, sẽ dùng default URL.

### Bước 5: Test Feature

#### Test 1: Tạo Payment và Verify

```bash
# 1. Tạo payment
curl -X POST https://beitiscup-production.up.railway.app/api/tournament/create-payment \
  -H "Content-Type: application/json" \
  -d '{"order_id": "YOUR_ORDER_ID"}'

# 2. Sau khi thanh toán, verify
curl -X POST https://beitiscup-production.up.railway.app/api/tournament/verify-payment/YOUR_ORDER_ID
```

#### Test 2: Auto-check trong Team Status

```bash
# Poll team status - sẽ tự động query MoMo nếu chưa thanh toán
curl https://beitiscup-production.up.railway.app/api/tournament/team-status/YOUR_ORDER_ID
```

Expected response nếu thanh toán thành công:
```json
{
  "success": true,
  "data": {
    "team_id": 123,
    "team_name": "Example Team",
    "order_id": "ITIS_...",
    "status": "PAID_CONFIRMED",
    "paid_at": "2025-12-22T14:30:00",
    "created_at": "2025-12-22T14:00:00"
  }
}
```

## Cách Sử Dụng từ Frontend

### Option 1: Auto-check (Khuyến nghị)

Frontend chỉ cần poll endpoint `/team-status/{order_id}` như cũ:

```javascript
// Sau khi user thanh toán, poll status
const checkStatus = async (orderId) => {
  const response = await fetch(`/api/tournament/team-status/${orderId}`);
  const data = await response.json();
  
  if (data.data.status === 'PAID_CONFIRMED') {
    // Thanh toán thành công
    showSuccessMessage();
  } else if (data.data.status === 'PAID_REJECTED') {
    // Thanh toán thành công nhưng hết slot
    showRejectedMessage();
  }
  // Nếu vẫn REGISTERED, tiếp tục poll
};

// Poll mỗi 3 giây
const interval = setInterval(() => checkStatus(orderId), 3000);
```

### Option 2: Manual Verify (Optional)

Thêm button "Kiểm tra thanh toán" để user chủ động trigger:

```javascript
const verifyPayment = async (orderId) => {
  try {
    const response = await fetch(`/api/tournament/verify-payment/${orderId}`, {
      method: 'POST'
    });
    const data = await response.json();
    
    if (data.success) {
      alert('Thanh toán thành công!');
    } else {
      alert(data.message);
    }
  } catch (error) {
    alert('Có lỗi khi kiểm tra thanh toán');
  }
};
```

## Rollback (Nếu cần)

Nếu có vấn đề, rollback migration:

```bash
railway run python -m alembic downgrade -1
```

Hoặc deploy lại commit trước đó:

```bash
git revert HEAD
git push origin main
```

## Troubleshooting

### Migration lỗi

Nếu migration lỗi "column already exists":
```bash
# Đánh dấu migration đã chạy mà không thực sự chạy
railway run python -m alembic stamp fbe4bf76bbd3
```

### MoMo Query API trả về lỗi

- Kiểm tra `MOMO_QUERY_URL` đã đúng chưa
- Kiểm tra signature có đúng không (logs sẽ có thông tin)
- Đảm bảo `request_id` đã được lưu trong database

### Request ID không được lưu

Nếu teams cũ không có `request_id`:
- User cần tạo lại payment link mới
- Endpoint `/create-payment` sẽ tạo order_id mới và lưu request_id

## Monitoring

Sau khi deploy, theo dõi logs trên Railway:

```bash
railway logs
```

Các log quan trọng:
- `🔍 Querying MoMo transaction` - Query được gọi
- `✅ MoMo query successful` - Query thành công
- `✅ Team confirmed via MoMo query` - Team được confirm qua query

## Notes

- Feature này là **bổ sung** cho IPN webhook, không thay thế
- IPN vẫn là cách chính để cập nhật status
- Query API chỉ được dùng khi:
  - Frontend poll `/team-status`
  - User click button "Kiểm tra thanh toán"
- Không spam MoMo API - frontend nên poll với interval hợp lý (3-5 giây)

