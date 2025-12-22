# Test Payment Verification Feature

## Prerequisites

1. Backend đã deploy và đang chạy
2. Database migration đã chạy xong (có column `request_id` trong table `teams`)
3. Có một team đã đăng ký và có payment link

## Test Cases

### Test Case 1: Tạo Payment Link và Lưu Request ID

**Mục đích**: Đảm bảo `request_id` được lưu khi tạo payment

```bash
# 1. Đăng ký team mới
curl -X POST https://beitiscup-production.up.railway.app/api/tournament/register \
  -F "email=test@example.com" \
  -F "team_name=Test Team" \
  -F "leader_name=John Doe" \
  -F "leader_student_id=123456" \
  -F "phone=0123456789" \
  -F "vice_leader_name=Jane Doe" \
  -F "vice_leader_student_id=654321" \
  -F "vice_leader_phone=0987654321" \
  -F "members_list_text=Member 1, Member 2"

# Response sẽ có order_id
# Lưu order_id để dùng cho test tiếp theo
```

**Expected Result**:
- Response có `order_id`
- Response có `pay_url` và `qr_code_url`
- Database có record với `request_id` đã được lưu

**Verify trong Database**:
```sql
-- Chạy trên Railway database
SELECT order_id, request_id, status FROM teams 
WHERE order_id = 'YOUR_ORDER_ID';
```

Expected:
```
order_id         | request_id      | status
ITIS_...         | 1703251234567   | REGISTERED
```

---

### Test Case 2: Auto-check Payment Status

**Mục đích**: Endpoint `/team-status` tự động query MoMo khi team chưa thanh toán

**Steps**:

1. **Trước khi thanh toán** - Check status:
```bash
curl https://beitiscup-production.up.railway.app/api/tournament/team-status/YOUR_ORDER_ID
```

Expected response:
```json
{
  "success": true,
  "data": {
    "team_id": 1,
    "order_id": "ITIS_...",
    "status": "REGISTERED",
    "paid_at": null
  }
}
```

2. **Thanh toán qua MoMo** - Scan QR hoặc click payment link

3. **Sau khi thanh toán thành công** - Check status lại:
```bash
curl https://beitiscup-production.up.railway.app/api/tournament/team-status/YOUR_ORDER_ID
```

Expected response (nếu query thành công):
```json
{
  "success": true,
  "data": {
    "team_id": 1,
    "order_id": "ITIS_...",
    "status": "PAID_CONFIRMED",
    "paid_at": "2025-12-22T14:30:00"
  }
}
```

**Expected Logs**:
```
🔍 Team X not yet paid, querying MoMo for status...
🔍 Querying MoMo transaction: order_id=ITIS_..., request_id=...
MoMo Query Response: resultCode=0, message=Successful
✅ MoMo query successful: orderId=ITIS_..., payment confirmed
✅ Team X confirmed via MoMo query
```

---

### Test Case 3: Manual Verify Payment

**Mục đích**: User có thể chủ động trigger verification

```bash
curl -X POST https://beitiscup-production.up.railway.app/api/tournament/verify-payment/YOUR_ORDER_ID
```

**Case 3.1**: Chưa thanh toán

Expected response:
```json
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
```

**Case 3.2**: Đã thanh toán thành công

Expected response:
```json
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
```

**Case 3.3**: Đã thanh toán nhưng hết slot (>16 đội)

Expected response:
```json
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

---

### Test Case 4: Race Condition - Concurrent Payments

**Mục đích**: Đảm bảo chỉ có 16 đội đầu tiên được confirm

**Setup**:
- Tạo 20 teams
- 20 teams cùng thanh toán gần như đồng thời

**Steps**:

1. Tạo 20 teams:
```bash
for i in {1..20}; do
  curl -X POST https://beitiscup-production.up.railway.app/api/tournament/register \
    -F "email=test$i@example.com" \
    -F "team_name=Team $i" \
    -F "leader_name=Leader $i" \
    -F "leader_student_id=$i" \
    -F "phone=012345678$i" \
    -F "vice_leader_name=Vice $i" \
    -F "vice_leader_student_id=100$i" \
    -F "vice_leader_phone=098765432$i"
done
```

2. Giả lập thanh toán thành công bằng manual verify:
```bash
# Lấy danh sách order_ids
curl https://beitiscup-production.up.railway.app/api/tournament/teams | jq '.data.teams[].order_id'

# Verify tất cả cùng lúc (parallel)
for order_id in $(curl -s https://beitiscup-production.up.railway.app/api/tournament/teams | jq -r '.data.teams[].order_id'); do
  curl -X POST https://beitiscup-production.up.railway.app/api/tournament/verify-payment/$order_id &
done
wait
```

3. Check kết quả:
```bash
curl https://beitiscup-production.up.railway.app/api/tournament/teams | jq '.data'
```

**Expected Result**:
- Đúng 16 teams có status = `PAID_CONFIRMED`
- 4 teams còn lại có status = `PAID_REJECTED`
- Không có duplicate confirmations

---

### Test Case 5: IPN Webhook vẫn hoạt động

**Mục đích**: Đảm bảo IPN webhook vẫn là primary method

**Steps**:

1. Tạo payment mới
2. Thanh toán qua MoMo
3. **KHÔNG** gọi verify endpoint
4. Đợi IPN webhook từ MoMo (có thể mất vài giây)

**Expected Result**:
- Status được cập nhật tự động qua IPN
- Logs hiển thị:
```
✅ MoMo IPN received: orderId=..., resultCode=0
✅ MoMo IPN: Team confirmed - orderId=...
```

---

### Test Case 6: Duplicate Protection

**Mục đích**: Tránh duplicate updates khi cả IPN và manual verify cùng chạy

**Steps**:

1. Tạo payment và thanh toán
2. Gọi manual verify nhiều lần liên tục:
```bash
for i in {1..10}; do
  curl -X POST https://beitiscup-production.up.railway.app/api/tournament/verify-payment/YOUR_ORDER_ID &
done
wait
```

**Expected Result**:
- Team chỉ được cập nhật 1 lần
- Các requests sau trả về "Đội này đã được xác nhận thanh toán trước đó"
- Confirmed count vẫn đúng (không bị tăng sai)

---

## Performance Testing

### Test API Response Time

```bash
# Test team-status endpoint
time curl https://beitiscup-production.up.railway.app/api/tournament/team-status/YOUR_ORDER_ID

# Expected: < 2 seconds (bao gồm query MoMo)
```

### Test Load

```bash
# Giả lập 100 concurrent requests
for i in {1..100}; do
  curl https://beitiscup-production.up.railway.app/api/tournament/team-status/YOUR_ORDER_ID &
done
wait

# Expected: Tất cả requests đều thành công, không có timeout
```

---

## Error Cases

### Test Case E1: Order ID không tồn tại

```bash
curl https://beitiscup-production.up.railway.app/api/tournament/team-status/INVALID_ORDER_ID
```

Expected: HTTP 404
```json
{
  "detail": "Không tìm thấy đội với order_id này"
}
```

### Test Case E2: Không có request_id (team cũ)

```bash
# Với team được tạo trước khi có feature này
curl -X POST https://beitiscup-production.up.railway.app/api/tournament/verify-payment/OLD_ORDER_ID
```

Expected: HTTP 400
```json
{
  "detail": "Không thể xác thực thanh toán. Vui lòng thử tạo lại link thanh toán."
}
```

**Fix**: User cần tạo payment link mới:
```bash
curl -X POST https://beitiscup-production.up.railway.app/api/tournament/create-payment \
  -H "Content-Type: application/json" \
  -d '{"order_id": "OLD_ORDER_ID"}'
```

### Test Case E3: MoMo API timeout

**Simulate**: Tạm thời block outbound connection đến MoMo API

Expected:
- Endpoint trả về error sau timeout
- Logs hiển thị connection error
- Frontend nên retry sau vài giây

---

## Checklist

- [ ] Test Case 1: Request ID được lưu
- [ ] Test Case 2: Auto-check hoạt động
- [ ] Test Case 3.1: Manual verify khi chưa thanh toán
- [ ] Test Case 3.2: Manual verify khi đã thanh toán
- [ ] Test Case 3.3: Manual verify khi hết slot
- [ ] Test Case 4: Race condition handling
- [ ] Test Case 5: IPN vẫn hoạt động
- [ ] Test Case 6: Duplicate protection
- [ ] Performance: Response time < 2s
- [ ] Performance: Handle 100 concurrent requests
- [ ] Error Case E1: Invalid order ID
- [ ] Error Case E2: Missing request_id
- [ ] Error Case E3: MoMo timeout

---

## Rollback Plan

Nếu feature có vấn đề nghiêm trọng:

1. Rollback code:
```bash
git revert HEAD
git push origin main
```

2. Rollback migration (nếu cần):
```bash
railway run python -m alembic downgrade -1
```

3. Monitor logs để đảm bảo service ổn định

4. IPN webhook vẫn hoạt động bình thường (không bị ảnh hưởng)

