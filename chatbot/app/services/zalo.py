"""
Zalo Service
Gửi tin nhắn ZNS (Zalo Notification Service) tới khách hàng.
"""
import httpx
from app.core.config import settings
from app.core.logging import StructuredLogger
from typing import Dict, Any

logger = StructuredLogger(__name__)

class ZaloService:
    def __init__(self):
        self.api_url = "https://business.openapi.zalo.me/message/template"

    async def send_zns(self, phone: str, customer_name: str, order_code: str = ""):
        """
        Gửi tin nhắn ZNS chào mừng/xác nhận.
        Lưu ý: Cần đăng ký Template với Zalo trước.
        """
        token = settings.ZALO_ACCESS_TOKEN
        template_id = settings.ZALO_TEMPLATE_ID

        if not token or not template_id:
            logger.warning("zalo.config_missing", detail="Chưa cấu hình ZALO_ACCESS_TOKEN hoặc ZALO_TEMPLATE_ID")
            return

        # Chuẩn hóa số điện thoại (84xxx)
        phone = phone.strip()
        if phone.startswith("0"):
            phone = "84" + phone[1:]

        headers = {
            "access_token": token,
            "Content-Type": "application/json"
        }

        # Dữ liệu mẫu (cần khớp với template đã đăng ký trên Zalo OA)
        # Ví dụ template: "Chào {customer_name}, cảm ơn bạn đã quan tâm. Mã KH của bạn là {order_code}"
        payload = {
            "phone": phone,
            "template_id": template_id,
            "template_data": {
                "customer_name": customer_name,
                "order_code": order_code or "N/A"
            },
            "tracking_id": order_code
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                data = response.json()
                
                if data.get("error") == 0:
                    logger.info("zalo.sent_success", phone=phone)
                else:
                    logger.error("zalo.sent_failed", error=data.get("message"), detail=data)
        except Exception as e:
            logger.error("zalo.request_error", error=str(e))

zalo_service = ZaloService()