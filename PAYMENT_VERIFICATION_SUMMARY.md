# Payment Verification Feature - Summary

## Vấn Đề

Sau khi user thanh toán qua MoMo, IPN webhook không được gọi (hoặc bị delay), dẫn đến:
- Frontend poll `/team-status` nhiều lần nhưng status không cập nhật
- User không biết thanh toán đã thành công hay chưa
- Phải đợi MoMo gọi IPN webhook (có thể mất vài phút hoặc không bao giờ được gọi)

## Giải Pháp

Thêm khả năng **chủ động query MoMo API** để kiểm tra trạng thái thanh toán, thay vì chỉ phụ thuộc vào IPN webhook.

### Cơ chế hoạt động:

```
┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
│   Frontend  │                  │   Backend   │                  │    MoMo     │
└─────────────┘                  └─────────────┘                  └─────────────┘
       │                                │                                 │
       │ 1. POST /create-payment        │                                 │
       ├───────────────────────────────>│                                 │
       │                                │ 2. Create payment               │
       │                                ├────────────────────────────────>│
       │                                │ 3. Payment link + request_id    │
       │                                │<────────────────────────────────┤
       │ 4. Payment link + order_id     │                                 │
       │<───────────────────────────────┤                                 │
       │                                │ 5. Lưu request_id vào DB        │
       │                                │                                 │
       │ 6. User thanh toán             │                                 │
       ├────────────────────────────────────────────────────────────────>│
       │                                │                                 │
       │ 7. Poll /team-status/{orderId} │                                 │
       ├───────────────────────────────>│                                 │
       │                                │ 8. Query transaction (nếu chưa paid)
       │                                ├────────────────────────────────>│
       │                                │ 9. Transaction status            │
       │                                │<────────────────────────────────┤
       │                                │ 10. Update team status          │
       │ 11. Updated status             │                                 │
       │<───────────────────────────────┤                                 │
       │                                │                                 │
       │                                │ 12. IPN webhook (optional)      │
       │                                │<────────────────────────────────┤
```

## Các Thay Đổi

### 1. Database Schema

**Thêm column mới trong table `teams`**:
- `request_id` (String, nullable, indexed)

```sql
ALTER TABLE teams ADD COLUMN request_id VARCHAR(100);
CREATE INDEX ix_teams_request_id ON teams(request_id);
```

**Migration file**: `alembic/versions/fbe4bf76bbd3_add_request_id_to_teams.py`

### 2. Backend Code Changes

#### A. `app/services/momo_service.py`

**Thêm**:
- `self.query_url` - URL của MoMo Query API
- `query_transaction(order_id, request_id)` - Method query transaction status

**Update**:
- `create_payment_link()` - Trả về thêm `requestId` trong response

#### B. `app/routers/tournament.py`

**Thêm endpoint mới**:
```python
POST /api/tournament/verify-payment/{order_id}
```
- Cho phép frontend/user chủ động trigger verification
- Query MoMo API để check payment status
- Tự động cập nhật team status nếu payment thành công

**Update endpoint**:
```python
GET /api/tournament/team-status/{order_id}
```
- Tự động query MoMo nếu team chưa thanh toán (status = REGISTERED)
- Cập nhật status realtime
- Frontend không cần thay đổi gì, chỉ cần poll như bình thường

**Update payment creation**:
- Lưu `request_id` vào database khi tạo payment link
- Áp dụng cho cả `/register` và `/create-payment` endpoints

#### C. `app/models.py`

**Thêm column**:
```python
request_id = Column(String(100), nullable=True, index=True, 
                   comment="Request ID MoMo để query transaction")
```

### 3. Documentation

Tạo 3 file documentation:

1. **DEPLOY_PAYMENT_VERIFICATION.md** - Hướng dẫn deploy lên production
2. **TEST_PAYMENT_VERIFICATION.md** - Test cases và verification checklist
3. **PAYMENT_VERIFICATION_SUMMARY.md** - File này

## API Endpoints

### 1. GET `/api/tournament/team-status/{order_id}` (Updated)

**Cách hoạt động**:
- Nếu team đã thanh toán → Trả về status hiện tại
- Nếu team chưa thanh toán VÀ có request_id:
  - Tự động query MoMo API
  - Nếu MoMo confirm đã thanh toán → Cập nhật status
  - Trả về status mới nhất

**Frontend không cần thay đổi**, chỉ cần poll endpoint này như trước.

### 2. POST `/api/tournament/verify-payment/{order_id}` (New)

**Sử dụng khi**:
- User click button "Kiểm tra thanh toán"
- Cần force check payment status ngay lập tức

**Response**:
```json
// Thành công
{
  "success": true,
  "message": "Thanh toán thành công! Đội của bạn đã được xác nhận.",
  "data": {
    "order_id": "ITIS_...",
    "status": "PAID_CONFIRMED",
    "paid_at": "2025-12-22T14:30:00",
    "confirmed_count": 5
  }
}

// Chưa thanh toán
{
  "success": false,
  "message": "Thanh toán chưa thành công. Transaction not found",
  "data": {
    "order_id": "ITIS_...",
    "status": "REGISTERED",
    "momo_result_code": 1006,
    "momo_message": "Transaction not found"
  }
}

// Hết slot
{
  "success": false,
  "message": "Thanh toán thành công nhưng giải đấu đã đủ 16 đội.",
  "data": {
    "order_id": "ITIS_...",
    "status": "PAID_REJECTED",
    "paid_at": "2025-12-22T14:30:00"
  }
}
```

## Frontend Integration

### Option 1: Auto-check (Khuyến nghị)

Không cần thay đổi gì, frontend poll như cũ:

```javascript
const checkStatus = async (orderId) => {
  const response = await fetch(`/api/tournament/team-status/${orderId}`);
  const data = await response.json();
  
  if (data.data.status === 'PAID_CONFIRMED') {
    // Thanh toán thành công
    clearInterval(pollingInterval);
    showSuccessMessage();
  }
};

// Poll mỗi 3 giây
const pollingInterval = setInterval(() => checkStatus(orderId), 3000);
```

**Backend sẽ tự động query MoMo mỗi lần frontend poll.**

### Option 2: Manual verify button (Optional)

Thêm button để user chủ động check:

```javascript
<button onClick={() => verifyPayment(orderId)}>
  Kiểm tra thanh toán
</button>

const verifyPayment = async (orderId) => {
  const response = await fetch(`/api/tournament/verify-payment/${orderId}`, {
    method: 'POST'
  });
  const data = await response.json();
  
  if (data.success) {
    alert('Thanh toán thành công!');
  } else {
    alert(data.message);
  }
};
```

## Environment Variables

Cần thêm (hoặc verify) biến môi trường:

```env
# Existing
MOMO_API_URL=https://test-payment.momo.vn/v2/gateway/api/create
MOMO_PARTNER_CODE=...
MOMO_ACCESS_KEY=...
MOMO_SECRET_KEY=...
MOMO_NOTIFY_URL=https://beitiscup-production.up.railway.app/api/tournament/momo-ipn
MOMO_RETURN_URL=...

# New (optional, có default value)
MOMO_QUERY_URL=https://test-payment.momo.vn/v2/gateway/api/query
```

Nếu không set `MOMO_QUERY_URL`, sẽ dùng URL mặc định.

## Deployment Steps

### 1. Push code lên repository
```bash
git add .
git commit -m "Add payment verification with MoMo query API"
git push origin main
```

### 2. Railway auto-deploy

Railway sẽ tự động deploy service mới.

### 3. Chạy migration

**SSH vào Railway và chạy migration**:
```bash
railway connect
cd python-backend
python -m alembic upgrade head
```

Hoặc dùng Railway CLI:
```bash
railway run python -m alembic upgrade head
```

### 4. Verify

```bash
# Test endpoint
curl https://beitiscup-production.up.railway.app/api/tournament/team-status/YOUR_ORDER_ID
```

## Benefits

### 1. Giảm phụ thuộc vào IPN webhook
- IPN có thể bị delay hoặc không được gọi
- Query API cho kết quả realtime

### 2. Better UX
- User thấy status update ngay lập tức
- Không cần đợi IPN webhook

### 3. Fallback mechanism
- IPN là primary method
- Query API là fallback khi IPN không hoạt động

### 4. Không breaking changes
- Frontend không cần thay đổi gì
- API backward compatible

## Race Condition Handling

Vẫn giữ nguyên logic xử lý race condition:
- Database transaction với `SELECT FOR UPDATE`
- Lock rows khi đếm số đội confirmed
- Đảm bảo chỉ có đúng 16 đội được confirm

## Monitoring

Logs quan trọng cần theo dõi:

```
🔍 Team X not yet paid, querying MoMo for status...
🔍 Querying MoMo transaction: order_id=..., request_id=...
MoMo Query Response: resultCode=0, message=Successful
✅ MoMo query successful: orderId=..., payment confirmed
✅ Team X confirmed via MoMo query
```

## Limitations

1. **Requires request_id**
   - Teams cũ (tạo trước feature này) không có request_id
   - Solution: User cần tạo lại payment link mới

2. **MoMo API rate limit**
   - MoMo có thể rate limit nếu query quá nhiều
   - Frontend nên poll với interval hợp lý (3-5 giây)

3. **Not realtime như IPN**
   - Query chỉ được trigger khi frontend poll
   - IPN vẫn là cách tốt nhất để update realtime

## Rollback Plan

Nếu có vấn đề:

1. Rollback code:
```bash
git revert HEAD
git push origin main
```

2. Rollback migration (nếu cần):
```bash
railway run python -m alembic downgrade -1
```

3. IPN webhook vẫn hoạt động bình thường

## Files Changed

- ✅ `app/models.py` - Thêm request_id column
- ✅ `app/services/momo_service.py` - Thêm query_transaction method
- ✅ `app/routers/tournament.py` - Update endpoints
- ✅ `alembic/versions/fbe4bf76bbd3_add_request_id_to_teams.py` - Migration
- ✅ `DEPLOY_PAYMENT_VERIFICATION.md` - Deployment guide
- ✅ `TEST_PAYMENT_VERIFICATION.md` - Test cases
- ✅ `PAYMENT_VERIFICATION_SUMMARY.md` - This file

## Next Steps

1. Deploy code lên Railway
2. Chạy migration
3. Test với payment thật
4. Monitor logs
5. Update frontend (optional) để thêm "Kiểm tra thanh toán" button

---

**Status**: ✅ Ready for deployment
**Priority**: High (Fix critical issue với payment verification)
**Risk**: Low (Backward compatible, có rollback plan)

