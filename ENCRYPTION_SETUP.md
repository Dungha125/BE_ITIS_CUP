# API Encryption Setup Guide

## Tổng Quan

Đã implement encryption cho tất cả tournament APIs để bảo vệ dữ liệu khỏi bị xem qua Developer Tools (F12).

### Cách hoạt động:

```
Frontend Request → Backend API → Process Data → Encrypt Response → Return Encrypted Data
                                                                            ↓
Frontend Decrypt ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

## Setup Backend (Railway)

### Bước 1: Deploy Code

Code đã được update với encryption. Chỉ cần push lên Railway:

```bash
git add .
git commit -m "Add API encryption for tournament endpoints"
git push origin main
```

Railway sẽ tự động:
1. Pull code mới
2. Install dependencies (bao gồm `cryptography`)
3. Deploy service

### Bước 2: Set Environment Variables

Trên Railway Dashboard:

1. Vào project `beitiscup-production`
2. Click tab "Variables"
3. Thêm 2 biến mới:

```env
ENCRYPTION_SECRET=itiscup2024_secret_key_32byte
ENCRYPTION_IV=itiscup2024_iv16
```

**Khuyến nghị**: Dùng script để generate keys random:

```bash
python generate_encryption_keys.py
```

Copy keys từ output và paste vào Railway.

### Bước 3: Verify

Test một endpoint để xem encryption có hoạt động:

```bash
curl https://beitiscup-production.up.railway.app/api/tournament/teams
```

Response sẽ có format:

```json
{
  "encrypted": true,
  "data": "long_base64_encrypted_string_here..."
}
```

Nếu thấy format này → Encryption đã hoạt động! ✅

## Setup Frontend

### Bước 1: Install Dependencies

```bash
npm install crypto-js
# hoặc
yarn add crypto-js
```

### Bước 2: Tạo Crypto Utility

Tạo file `lib/crypto-utils.js` hoặc `utils/crypto.js`:

```javascript
import CryptoJS from 'crypto-js';

// Keys phải giống với backend
const ENCRYPTION_SECRET = process.env.NEXT_PUBLIC_ENCRYPTION_SECRET || 'itiscup2024_secret_key_32byte';
const ENCRYPTION_IV = process.env.NEXT_PUBLIC_ENCRYPTION_IV || 'itiscup2024_iv16';

/**
 * Giải mã response từ backend
 */
export function decryptResponse(encryptedData) {
  try {
    const key = CryptoJS.enc.Utf8.parse(ENCRYPTION_SECRET.padEnd(32, '0').substring(0, 32));
    const iv = CryptoJS.enc.Utf8.parse(ENCRYPTION_IV.padEnd(16, '0').substring(0, 16));
    
    const decrypted = CryptoJS.AES.decrypt(encryptedData, key, {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    });
    
    const decryptedStr = decrypted.toString(CryptoJS.enc.Utf8);
    return JSON.parse(decryptedStr);
  } catch (error) {
    console.error('Decryption error:', error);
    throw error;
  }
}

/**
 * Fetch và tự động giải mã
 */
export async function fetchEncrypted(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  
  // Tự động giải mã nếu response được encrypt
  if (data.encrypted === true && data.data) {
    return decryptResponse(data.data);
  }
  
  return data;
}
```

### Bước 3: Set Environment Variables

Tạo file `.env.local` (Next.js) hoặc `.env` (React):

```env
NEXT_PUBLIC_ENCRYPTION_SECRET=itiscup2024_secret_key_32byte
NEXT_PUBLIC_ENCRYPTION_IV=itiscup2024_iv16
```

**LƯU Ý**: Keys phải giống với backend!

### Bước 4: Update API Calls

#### Cách 1: Replace fetch calls

```javascript
// Trước
const response = await fetch('/api/tournament/teams');
const data = await response.json();

// Sau
import { fetchEncrypted } from '@/lib/crypto-utils';
const data = await fetchEncrypted('/api/tournament/teams');
```

#### Cách 2: Wrapper cho axios

```javascript
import axios from 'axios';
import { decryptResponse } from '@/lib/crypto-utils';

// Interceptor để tự động giải mã
axios.interceptors.response.use(response => {
  const data = response.data;
  
  if (data.encrypted === true && data.data) {
    response.data = decryptResponse(data.data);
  }
  
  return response;
});

// Usage - không cần thay đổi gì
const { data } = await axios.get('/api/tournament/teams');
```

### Bước 5: Test

```javascript
import { fetchEncrypted } from '@/lib/crypto-utils';

async function testEncryption() {
  try {
    const data = await fetchEncrypted('/api/tournament/teams');
    console.log('Decrypted data:', data);
    // Nên thấy data bình thường, không phải base64 string
  } catch (error) {
    console.error('Error:', error);
  }
}
```

## Các Endpoint Được Mã Hóa

✅ Encrypted:
- `POST /api/tournament/register`
- `POST /api/tournament/create-payment`
- `GET /api/tournament/team-status/{order_id}`
- `GET /api/tournament/my-teams`
- `GET /api/tournament/teams`
- `POST /api/tournament/verify-payment/{order_id}`

❌ Không encrypted:
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `GET /health`
- `/docs`

## Security Best Practices

### 1. Key Management

**Development**:
```env
ENCRYPTION_SECRET=itiscup2024_secret_key_32byte
ENCRYPTION_IV=itiscup2024_iv16
```

**Production** (Generate random keys):
```bash
python generate_encryption_keys.py
```

### 2. Don't Commit Keys

Thêm vào `.gitignore`:
```
.env
.env.local
.env.production
```

### 3. Rotate Keys Regularly

Mỗi 3-6 tháng:
1. Generate keys mới
2. Update backend (Railway)
3. Update frontend
4. Deploy cả 2 cùng lúc

### 4. HTTPS Required

- Encryption không thay thế HTTPS
- Railway tự động dùng HTTPS
- Frontend cũng phải dùng HTTPS trong production

## Troubleshooting

### Error: "Decryption failed"

**Nguyên nhân**: Keys không khớp

**Giải pháp**:
1. Check backend logs xem có encryption logs không
2. Verify keys trong Railway Variables
3. Verify keys trong frontend .env
4. Clear browser cache và reload

### Response vẫn là plaintext

**Nguyên nhân**: Encryption middleware không hoạt động

**Giải pháp**:
1. Check Railway logs: `railway logs`
2. Tìm log: `EncryptionService initialized`
3. Nếu không thấy → dependencies chưa install
4. Redeploy: `railway redeploy`

### Frontend không decode được

**Nguyên nhân**: Sai keys hoặc sai implementation

**Giải pháp**:
```javascript
// Test với sample data
const testKey = 'itiscup2024_secret_key_32byte';
const testIV = 'itiscup2024_iv16';

console.log('Key length:', testKey.length); // Must be 32
console.log('IV length:', testIV.length);   // Must be 16
```

## Performance Impact

- Encryption overhead: ~1-2ms
- Response size increase: ~30% (due to base64)
- Total impact: Negligible (< 50ms added latency)

## Migration from Unencrypted

Nếu đang có code chạy production:

### Plan A: Gradual Migration (Khuyến nghị)

1. Deploy backend với encryption (không break frontend cũ)
2. Update frontend để support cả encrypted và unencrypted
3. Test thoroughly
4. Deploy frontend mới

Frontend code:
```javascript
export async function fetchWithFallback(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  
  // Support both encrypted and unencrypted
  if (data.encrypted === true && data.data) {
    try {
      return decryptResponse(data.data);
    } catch (error) {
      console.error('Decryption failed, using raw data');
      return data;
    }
  }
  
  return data;
}
```

### Plan B: Hard Switch

1. Deploy backend + frontend cùng lúc
2. Downtime: ~5 phút
3. Rollback nhanh nếu có vấn đề

## Monitoring

### Backend Logs

Tìm logs này để verify encryption:

```
✅ EncryptionService initialized
✅ Encrypted response for: /api/tournament/teams
```

### Frontend Monitoring

```javascript
// Log mỗi lần decrypt
const originalDecrypt = decryptResponse;
export function decryptResponse(data) {
  console.log('Decrypting data...');
  const result = originalDecrypt(data);
  console.log('Decryption success');
  return result;
}
```

## Rollback Plan

Nếu có vấn đề nghiêm trọng:

### Backend Rollback

```python
# app/main.py
# Comment out encryption middleware
# app.add_middleware(EncryptionMiddleware, ...)
```

Push lên Railway → Auto redeploy

### Frontend Rollback

```javascript
// Fallback to unencrypted
export async function fetchEncrypted(url, options) {
  // Just use normal fetch
  const response = await fetch(url, options);
  return await response.json();
}
```

## FAQs

**Q: Keys có bị lộ qua frontend code không?**
A: Có. Đây là obfuscation layer, không phải security tuyệt đối. Main security vẫn phải dựa vào authentication.

**Q: Có cần encrypt request data không?**
A: Hiện tại chưa cần. Response encryption đã đủ để ẩn data khỏi F12.

**Q: Có ảnh hưởng performance không?**
A: Minimal (~1-2ms). Không đáng kể.

**Q: Có thể dùng algorithm khác không?**
A: Có, nhưng phải update cả backend và frontend.

**Q: Production keys có khác dev keys không?**
A: Nên khác. Dùng `generate_encryption_keys.py` để tạo random keys cho production.

## Next Steps

1. ✅ Deploy backend lên Railway
2. ✅ Set environment variables
3. ✅ Test encryption với curl
4. ✅ Update frontend code
5. ✅ Test thoroughly
6. ✅ Monitor logs
7. ✅ Generate production keys (optional)

## Support

Xem chi tiết trong:
- `ENCRYPTION_GUIDE.md` - Frontend implementation guide
- `app/services/encryption_service.py` - Backend encryption service
- `app/middleware/encryption_middleware.py` - Encryption middleware

