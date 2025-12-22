"""
Middleware: Encryption
Tự động mã hóa response cho các endpoints được chỉ định
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json
import logging
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)


class EncryptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware tự động mã hóa response cho các endpoints tournament
    """

    def __init__(self, app, encrypted_paths: list = None):
        super().__init__(app)
        # Danh sách các path cần mã hóa
        self.encrypted_paths = encrypted_paths or [
            "/api/tournament/register",
            "/api/tournament/create-payment",
            "/api/tournament/team-status",
            "/api/tournament/my-teams",
            "/api/tournament/teams",
            "/api/tournament/verify-payment",
        ]

    async def dispatch(self, request: Request, call_next):
        # Gọi endpoint gốc
        response = await call_next(request)
        
        # Kiểm tra xem path có cần mã hóa không
        if not self._should_encrypt(request.path):
            return response
        
        # Chỉ encrypt response 200 và content-type là JSON
        if response.status_code != 200:
            return response
        
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return response
        
        try:
            # Đọc response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Parse JSON
            try:
                original_data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                # Không phải JSON hợp lệ, trả về response gốc
                return JSONResponse(
                    content=json.loads(body.decode('utf-8')) if body else {},
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            # Mã hóa data
            encrypted_response = encryption_service.encrypt_response(original_data)
            
            # Log để debug (không log data thật)
            logger.info(f"Encrypted response for: {request.path}")
            
            # Trả về response đã mã hóa
            return JSONResponse(
                content=encrypted_response,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except Exception as e:
            logger.error(f"Encryption middleware error: {str(e)}", exc_info=True)
            # Nếu có lỗi, trả về response gốc
            return response

    def _should_encrypt(self, path: str) -> bool:
        """
        Kiểm tra xem path có cần mã hóa không
        
        Args:
            path: Request path
            
        Returns:
            True nếu cần mã hóa
        """
        # Kiểm tra exact match hoặc startswith
        for encrypted_path in self.encrypted_paths:
            if path == encrypted_path or path.startswith(encrypted_path):
                return True
        return False

