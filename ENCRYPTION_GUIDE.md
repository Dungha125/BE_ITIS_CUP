# Hướng Dẫn Sử Dụng API Encryption

## Tổng Quan

Tất cả các API endpoint liên quan đến tournament đều được mã hóa bằng AES-256-CBC để bảo vệ dữ liệu. Frontend cần giải mã response trước khi sử dụng.

## Các Endpoint Được Mã Hóa

- `POST /api/tournament/register`
- `POST /api/tournament/create-payment`
- `GET /api/tournament/team-status/{order_id}`
- `GET /api/tournament/my-teams`
- `GET /api/tournament/teams`
- `POST /api/tournament/verify-payment/{order_id}`

## Format Response

### Response Đã Mã Hóa

```json
{
  "encrypted": true,
  "data": "base64_encrypted_string_here..."
}
```

### Response Gốc (Sau khi giải mã)

```json
{
  "success": true,
  "data": {
    "team_id": 1,
    "team_name": "Example Team",
    ...
  }
}
```

## Encryption Parameters

- **Algorithm**: AES-256-CBC
- **Key**: 32 bytes (từ environment variable `ENCRYPTION_SECRET`)
- **IV**: 16 bytes (từ environment variable `ENCRYPTION_IV`)
- **Padding**: PKCS7
- **Encoding**: Base64

## Frontend Implementation

### JavaScript/TypeScript

```javascript
// crypto-utils.js
import CryptoJS from 'crypto-js';

// Các giá trị này phải giống với backend
const ENCRYPTION_SECRET = 'itiscup2024_secret_key_32byte';
const ENCRYPTION_IV = 'itiscup2024_iv16';

/**
 * Giải mã response từ backend
 * @param {string} encryptedData - Chuỗi base64 đã mã hóa
 * @returns {object} - Dữ liệu đã giải mã
 */
export function decryptResponse(encryptedData) {
  try {
    // Convert key và IV sang format của CryptoJS
    const key = CryptoJS.enc.Utf8.parse(ENCRYPTION_SECRET.padEnd(32, '0').substring(0, 32));
    const iv = CryptoJS.enc.Utf8.parse(ENCRYPTION_IV.padEnd(16, '0').substring(0, 16));
    
    // Giải mã
    const decrypted = CryptoJS.AES.decrypt(encryptedData, key, {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    });
    
    // Convert sang string
    const decryptedStr = decrypted.toString(CryptoJS.enc.Utf8);
    
    // Parse JSON
    return JSON.parse(decryptedStr);
  } catch (error) {
    console.error('Decryption error:', error);
    throw error;
  }
}

/**
 * Fetch và tự động giải mã response
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<object>} - Dữ liệu đã giải mã
 */
export async function fetchEncrypted(url, options = {}) {
  try {
    const response = await fetch(url, options);
    const data = await response.json();
    
    // Kiểm tra xem response có được mã hóa không
    if (data.encrypted === true && data.data) {
      // Giải mã
      return decryptResponse(data.data);
    }
    
    // Nếu không được mã hóa, trả về data gốc
    return data;
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
}
```

### Installation

```bash
npm install crypto-js
# hoặc
yarn add crypto-js
```

### Usage Examples

#### Example 1: Lấy danh sách teams

```javascript
import { fetchEncrypted } from './crypto-utils';

async function getTeams() {
  try {
    const data = await fetchEncrypted('/api/tournament/teams');
    console.log(data); // Dữ liệu đã được giải mã tự động
    
    // {
    //   success: true,
    //   data: {
    //     teams: [...],
    //     confirmed_count: 5,
    //     max_teams: 16
    //   }
    // }
  } catch (error) {
    console.error('Error:', error);
  }
}
```

#### Example 2: Kiểm tra trạng thái team

```javascript
import { fetchEncrypted } from './crypto-utils';

async function checkTeamStatus(orderId) {
  try {
    const data = await fetchEncrypted(`/api/tournament/team-status/${orderId}`);
    
    if (data.success) {
      const { status, paid_at } = data.data;
      
      if (status === 'PAID_CONFIRMED') {
        console.log('Team đã được xác nhận!');
      } else if (status === 'REGISTERED') {
        console.log('Chưa thanh toán');
      }
    }
  } catch (error) {
    console.error('Error:', error);
  }
}
```

#### Example 3: Đăng ký team

```javascript
import { fetchEncrypted } from './crypto-utils';

async function registerTeam(formData) {
  try {
    const data = await fetchEncrypted('/api/tournament/register', {
      method: 'POST',
      body: formData // FormData object
    });
    
    if (data.success) {
      const { order_id, pay_url, qr_code_url } = data.data;
      console.log('Đăng ký thành công!');
      console.log('Payment URL:', pay_url);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}
```

### React Hook Example

```javascript
// useEncryptedApi.js
import { useState, useEffect } from 'react';
import { fetchEncrypted } from './crypto-utils';

export function useEncryptedApi(url, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await fetchEncrypted(url, options);
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [url]);

  return { data, loading, error };
}

// Usage
function TeamsList() {
  const { data, loading, error } = useEncryptedApi('/api/tournament/teams');

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data.data.teams.map(team => (
        <div key={team.id}>{team.team_name}</div>
      ))}
    </div>
  );
}
```

## Python Client Example

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import json
import requests

ENCRYPTION_SECRET = 'itiscup2024_secret_key_32byte'
ENCRYPTION_IV = 'itiscup2024_iv16'

def decrypt_response(encrypted_data: str) -> dict:
    """Giải mã response từ backend"""
    # Prepare key và IV
    key = ENCRYPTION_SECRET.encode('utf-8')[:32].ljust(32, b'0')
    iv = ENCRYPTION_IV.encode('utf-8')[:16].ljust(16, b'0')
    
    # Decode base64
    encrypted_bytes = base64.b64decode(encrypted_data)
    
    # Decrypt
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
    
    # Unpad
    unpadder = padding.PKCS7(128).unpadder()
    json_bytes = unpadder.update(padded_data) + unpadder.finalize()
    
    # Parse JSON
    return json.loads(json_bytes.decode('utf-8'))

def fetch_encrypted(url: str, **kwargs) -> dict:
    """Fetch và tự động giải mã"""
    response = requests.get(url, **kwargs)
    data = response.json()
    
    if data.get('encrypted') and data.get('data'):
        return decrypt_response(data['data'])
    
    return data

# Usage
teams = fetch_encrypted('https://beitiscup-production.up.railway.app/api/tournament/teams')
print(teams)
```

## Environment Variables

### Backend (Railway)

```env
ENCRYPTION_SECRET=itiscup2024_secret_key_32byte
ENCRYPTION_IV=itiscup2024_iv16
```

**LƯU Ý**: Trong production, nên đổi sang key phức tạp hơn và random.

### Frontend (.env)

```env
NEXT_PUBLIC_ENCRYPTION_SECRET=itiscup2024_secret_key_32byte
NEXT_PUBLIC_ENCRYPTION_IV=itiscup2024_iv16
```

## Security Notes

1. **Key Management**:
   - Không commit key vào git
   - Sử dụng environment variables
   - Trong production, dùng key random và mạnh

2. **HTTPS**:
   - Luôn sử dụng HTTPS trong production
   - Encryption không thay thế HTTPS

3. **Key Rotation**:
   - Định kỳ thay đổi encryption key
   - Có kế hoạch rollover key

4. **Frontend Security**:
   - Key sẽ visible trong browser code
   - Đây chỉ là obfuscation layer, không phải security tuyệt đối
   - Main security vẫn phải dựa vào authentication & authorization

## Troubleshooting

### Error: "Decryption failed"

**Nguyên nhân**: Key hoặc IV không khớp giữa backend và frontend

**Giải pháp**:
```javascript
// Kiểm tra key và IV
console.log('Key length:', ENCRYPTION_SECRET.length); // Phải = 32
console.log('IV length:', ENCRYPTION_IV.length);      // Phải = 16
```

### Error: "Invalid padding"

**Nguyên nhân**: Data bị corrupt hoặc key sai

**Giải pháp**:
- Kiểm tra base64 string có đầy đủ không
- Verify key và IV

### Response không được mã hóa

**Nguyên nhân**: Endpoint không trong danh sách encrypted_paths

**Giải pháp**:
- Kiểm tra `app/main.py` - danh sách `encrypted_paths`
- Thêm endpoint vào list nếu cần

## Testing

### Test Decryption

```javascript
import { decryptResponse } from './crypto-utils';

// Sample encrypted data từ backend
const sampleEncrypted = "base64_string_here...";

try {
  const decrypted = decryptResponse(sampleEncrypted);
  console.log('Decryption success:', decrypted);
} catch (error) {
  console.error('Decryption failed:', error);
}
```

### Test API Call

```bash
# Call API và check response format
curl https://beitiscup-production.up.railway.app/api/tournament/teams

# Response sẽ có format:
# {
#   "encrypted": true,
#   "data": "base64_encrypted_string..."
# }
```

## Performance

- Encryption/Decryption overhead: ~1-2ms
- Không ảnh hưởng đáng kể đến performance
- Data size tăng ~30% do base64 encoding

## Endpoints Không Mã Hóa

Các endpoint sau KHÔNG được mã hóa:
- `/api/auth/login`
- `/api/auth/register`
- `/api/auth/me`
- `/` (root)
- `/health`
- `/docs`

## Migration Plan

Nếu cần disable encryption:

1. Comment out middleware trong `app/main.py`:
```python
# app.add_middleware(EncryptionMiddleware, ...)
```

2. Frontend sẽ tự động fallback về unencrypted mode:
```javascript
if (data.encrypted === true) {
  // decrypt
} else {
  // use data directly
}
```

