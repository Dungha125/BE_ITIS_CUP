"""
Service: EncryptionService
Mã hóa/giải mã dữ liệu API để bảo mật
"""
import os
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service mã hóa dữ liệu bằng AES-256-CBC
    - Mã hóa response data để bảo vệ thông tin
    - Giải mã request data từ client
    """

    def __init__(self):
        # Lấy secret key từ environment (32 bytes cho AES-256)
        secret = os.getenv('ENCRYPTION_SECRET', 'itiscup2024_secret_key_32byte')
        # Đảm bảo key đúng 32 bytes
        self.key = secret.encode('utf-8')[:32].ljust(32, b'0')
        
        # IV (Initialization Vector) - 16 bytes cho AES
        iv_secret = os.getenv('ENCRYPTION_IV', 'itiscup2024_iv16')
        self.iv = iv_secret.encode('utf-8')[:16].ljust(16, b'0')
        
        logger.info("EncryptionService initialized")

    def encrypt_data(self, data: dict) -> str:
        """
        Mã hóa dictionary thành chuỗi base64
        
        Args:
            data: Dictionary cần mã hóa
            
        Returns:
            Chuỗi base64 đã mã hóa
        """
        try:
            # Convert dict to JSON string
            json_str = json.dumps(data, ensure_ascii=False)
            json_bytes = json_str.encode('utf-8')
            
            # Padding để đảm bảo độ dài chia hết cho block size (128 bit = 16 bytes)
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(json_bytes) + padder.finalize()
            
            # Mã hóa bằng AES-256-CBC
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(self.iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Encode sang base64 để truyền qua HTTP
            encrypted_base64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            return encrypted_base64
            
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}", exc_info=True)
            raise

    def decrypt_data(self, encrypted_str: str) -> dict:
        """
        Giải mã chuỗi base64 thành dictionary
        
        Args:
            encrypted_str: Chuỗi base64 đã mã hóa
            
        Returns:
            Dictionary đã giải mã
        """
        try:
            # Decode từ base64
            encrypted_data = base64.b64decode(encrypted_str)
            
            # Giải mã bằng AES-256-CBC
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(self.iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Unpadding
            unpadder = padding.PKCS7(128).unpadder()
            json_bytes = unpadder.update(padded_data) + unpadder.finalize()
            
            # Convert JSON string to dict
            json_str = json_bytes.decode('utf-8')
            data = json.loads(json_str)
            
            return data
            
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}", exc_info=True)
            raise

    def encrypt_response(self, response_data: dict) -> dict:
        """
        Mã hóa response data và wrap trong format chuẩn
        
        Args:
            response_data: Dictionary response gốc
            
        Returns:
            Dictionary với dữ liệu đã mã hóa
        """
        try:
            encrypted = self.encrypt_data(response_data)
            return {
                "encrypted": True,
                "data": encrypted
            }
        except Exception as e:
            logger.error(f"Failed to encrypt response: {str(e)}")
            # Fallback: trả về data gốc nếu encrypt fail
            return {
                "encrypted": False,
                "data": response_data
            }


# Singleton instance
encryption_service = EncryptionService()

