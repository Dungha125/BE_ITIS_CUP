"""
Script để generate random encryption keys
Chạy script này để tạo keys mới cho production
"""
import secrets
import string

def generate_key(length: int) -> str:
    """Generate random alphanumeric key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_encryption_keys():
    """Generate encryption secret và IV"""
    # AES-256 cần key 32 bytes
    secret = generate_key(32)
    
    # IV cần 16 bytes
    iv = generate_key(16)
    
    print("=" * 60)
    print("ENCRYPTION KEYS - Dùng cho Production")
    print("=" * 60)
    print()
    print("Backend Environment Variables (Railway):")
    print("-" * 60)
    print(f"ENCRYPTION_SECRET={secret}")
    print(f"ENCRYPTION_IV={iv}")
    print()
    print("Frontend Environment Variables (.env.local):")
    print("-" * 60)
    print(f"NEXT_PUBLIC_ENCRYPTION_SECRET={secret}")
    print(f"NEXT_PUBLIC_ENCRYPTION_IV={iv}")
    print()
    print("=" * 60)
    print("⚠️  LƯU Ý:")
    print("1. Copy các giá trị này vào Railway và Frontend .env")
    print("2. KHÔNG commit keys vào git")
    print("3. Giữ keys này bí mật")
    print("4. Backend và Frontend phải dùng cùng keys")
    print("=" * 60)

if __name__ == "__main__":
    generate_encryption_keys()

