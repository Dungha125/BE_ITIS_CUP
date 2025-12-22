"""
Service: MomoService
Xử lý tích hợp thanh toán MoMo Business
"""
import hmac
import hashlib
import httpx
import os
from typing import Optional, Dict
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class MomoService:
    """
    Service xử lý thanh toán MoMo Business
    - Tạo payment link/QR code
    - Xác thực chữ ký IPN webhook
    - Validate dữ liệu thanh toán
    """

    def __init__(self):
        # Lấy config từ environment variables
        self.api_url = os.getenv(
            "MOMO_API_URL",
            "https://test-payment.momo.vn/v2/gateway/api/create"
        )
        self.partner_code = os.getenv("MOMO_PARTNER_CODE", "")
        self.access_key = os.getenv("MOMO_ACCESS_KEY", "")
        self.secret_key = os.getenv("MOMO_SECRET_KEY", "")
        self.return_url = os.getenv("MOMO_RETURN_URL", "")
        self.notify_url = os.getenv("MOMO_NOTIFY_URL", "")
        self.partner_name = os.getenv("MOMO_PARTNER_NAME", "ITISCUP Tournament")
        self.store_id = os.getenv("MOMO_STORE_ID", "ITISCUP")
        
        # Log config (không log secret_key)
        logger.info(f"MoMo Service initialized: api_url={self.api_url}, partner_code={self.partner_code[:4]}..., has_secret_key={bool(self.secret_key)}")
        logger.info(f"MoMo URLs: return_url={self.return_url}, notify_url={self.notify_url}")
        
        # Cảnh báo nếu IPN URL không được set
        if not self.notify_url:
            logger.warning("⚠️  MOMO_NOTIFY_URL is not set! IPN webhook will not work!")

    def create_payment_link(
        self,
        order_id: str,
        amount: int,
        order_info: str = "",
        extra_data: str = "",
        return_url: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Tạo payment link/QR code từ MoMo

        Args:
            order_id: Mã đơn hàng duy nhất
            amount: Số tiền (VND)
            order_info: Thông tin đơn hàng
            extra_data: Dữ liệu bổ sung (JSON string)

        Returns:
            Dict với 'payUrl', 'qrCodeUrl', 'deeplink' hoặc None nếu lỗi
        """
        try:
            import time
            import random

            # Tạo requestId duy nhất
            request_id = f"{int(time.time())}{random.randint(1000, 9999)}"

            # Tạo requestType (captureWallet = thanh toán qua ví MoMo)
            request_type = "captureWallet"

            # Sử dụng return_url từ parameter hoặc mặc định
            redirect_url = return_url if return_url else self.return_url

            # Đảm bảo IPN URL không rỗng
            if not self.notify_url:
                logger.error("MOMO_NOTIFY_URL is not set! IPN will not work.")
                raise ValueError("MOMO_NOTIFY_URL environment variable is required")

            # Log IPN URL để debug
            logger.info(f"Using IPN URL: {self.notify_url}")

            # Tạo raw signature string
            raw_signature = (
                f"accessKey={self.access_key}"
                f"&amount={amount}"
                f"&extraData={extra_data}"
                f"&ipnUrl={self.notify_url}"
                f"&orderId={order_id}"
                f"&orderInfo={order_info}"
                f"&partnerCode={self.partner_code}"
                f"&redirectUrl={redirect_url}"
                f"&requestId={request_id}"
                f"&requestType={request_type}"
            )

            # Tạo chữ ký HMAC SHA256
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                raw_signature.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Tạo request body
            request_body = {
                "partnerCode": self.partner_code,
                "partnerName": self.partner_name,
                "storeId": self.store_id,
                "requestId": request_id,
                "amount": amount,
                "orderId": order_id,
                "orderInfo": order_info,
                "redirectUrl": redirect_url,
                "ipnUrl": self.notify_url,
                "lang": "vi",
                "extraData": extra_data,
                "requestType": request_type,
                "signature": signature,
            }

            # Gửi request đến MoMo API
            logger.info(f"Calling MoMo API: order_id={order_id}, amount={amount}, return_url={redirect_url}, ipn_url={self.notify_url}")
            logger.info(f"MoMo Request Body (without signature): { {k: v for k, v in request_body.items() if k != 'signature'} }")
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.api_url, json=request_body)

            logger.info(f"MoMo API Response: status={response.status_code}")
            
            if response.status_code != 200:
                logger.error(
                    f"MoMo API Error: status={response.status_code}, body={response.text}"
                )
                return None

            response_data = response.json()
            logger.info(f"MoMo API Response Data: resultCode={response_data.get('resultCode')}, message={response_data.get('message')}")

            # Kiểm tra resultCode (0 = thành công)
            if response_data.get("resultCode") == 0:
                pay_url = response_data.get("payUrl")
                qr_code_url = response_data.get("qrCodeUrl")
                deeplink = response_data.get("deeplink")
                
                logger.info(f"Payment link created successfully: payUrl={pay_url is not None}, qrCodeUrl={qr_code_url is not None}, deeplink={deeplink is not None}")
                
                return {
                    "payUrl": pay_url,
                    "qrCodeUrl": qr_code_url,
                    "deeplink": deeplink,
                }

            logger.error(
                f"MoMo Payment Creation Failed: "
                f"resultCode={response_data.get('resultCode')}, "
                f"message={response_data.get('message')}"
            )
            return None

        except Exception as e:
            logger.error(f"MoMo Service Exception: {str(e)}", exc_info=True)
            return None

    def verify_signature(self, data: Dict) -> bool:
        """
        Xác thực chữ ký từ IPN webhook của MoMo

        Args:
            data: Dữ liệu từ IPN webhook

        Returns:
            True nếu chữ ký hợp lệ, False nếu không
        """
        try:
            # Lấy chữ ký từ request
            received_signature = data.get("signature", "")

            if not received_signature:
                logger.warning("MoMo IPN: Missing signature")
                return False

            # Tạo raw signature string theo thứ tự của MoMo
            raw_signature = (
                f"accessKey={data.get('accessKey')}"
                f"&amount={data.get('amount')}"
                f"&extraData={data.get('extraData', '')}"
                f"&message={data.get('message', '')}"
                f"&orderId={data.get('orderId')}"
                f"&orderInfo={data.get('orderInfo', '')}"
                f"&orderType={data.get('orderType', '')}"
                f"&partnerCode={data.get('partnerCode')}"
                f"&payType={data.get('payType', '')}"
                f"&requestId={data.get('requestId')}"
                f"&responseTime={data.get('responseTime')}"
                f"&resultCode={data.get('resultCode')}"
                f"&transId={data.get('transId')}"
            )

            # Tạo chữ ký HMAC SHA256
            calculated_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                raw_signature.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # So sánh chữ ký (dùng hmac.compare_digest để tránh timing attack)
            is_valid = hmac.compare_digest(calculated_signature, received_signature)

            if not is_valid:
                logger.warning(
                    f"MoMo IPN: Invalid signature - "
                    f"received={received_signature[:20]}..., "
                    f"calculated={calculated_signature[:20]}..."
                )

            return is_valid

        except Exception as e:
            logger.error(f"MoMo Signature Verification Exception: {str(e)}", exc_info=True)
            return False

    def validate_ipn(self, data: Dict) -> Dict:
        """
        Validate dữ liệu IPN từ MoMo

        Args:
            data: Dữ liệu từ IPN webhook

        Returns:
            Dict với 'valid', 'orderId', 'amount', 'resultCode', 'transId', 'message'
        """
        result = {
            "valid": False,
            "orderId": None,
            "amount": None,
            "resultCode": None,
            "transId": None,
            "message": None,
        }

        try:
            # Kiểm tra các trường bắt buộc
            required_fields = [
                "partnerCode",
                "orderId",
                "amount",
                "resultCode",
                "transId",
                "signature",
            ]

            for field in required_fields:
                if field not in data:
                    logger.warning(f"MoMo IPN: Missing required field: {field}")
                    return result

            # Xác thực chữ ký
            if not self.verify_signature(data):
                return result

            # Kiểm tra partnerCode
            if data.get("partnerCode") != self.partner_code:
                logger.warning(
                    f"MoMo IPN: Invalid partnerCode - "
                    f"received={data.get('partnerCode')}, "
                    f"expected={self.partner_code}"
                )
                return result

            # Lấy thông tin
            result["valid"] = True
            result["orderId"] = data.get("orderId")
            result["amount"] = int(data.get("amount"))
            result["resultCode"] = int(data.get("resultCode"))
            result["transId"] = data.get("transId")
            result["message"] = data.get("message", "")

            return result

        except Exception as e:
            logger.error(f"MoMo IPN Validation Exception: {str(e)}", exc_info=True)
            return result

