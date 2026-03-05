"""
Dịch vụ DeepSeek LLM
Xử lý giao tiếp với API DeepSeek để hoàn thành cuộc trò chuyện
"""
import httpx
from typing import List, Dict, Optional
from app.core.config import settings
from app.core.logging import logger


class DeepSeekLLMService:
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        self.model = settings.DEEPSEEK_MODEL
        self.temperature = settings.DEEPSEEK_TEMPERATURE
        self.max_tokens = settings.DEEPSEEK_MAX_TOKENS
    
    def _validate_api_key(self) -> bool:
        """Kiểm tra xem API key đã được cấu hình chưa."""
        if not self.api_key:
            logger.warning("deepseek.no_api_key", msg="DEEPSEEK_API_KEY is not set")
            return False
        return True
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Gửi tin nhắn đến API DeepSeek và nhận phản hồi.
        
        Args:
            messages: Danh sách các dict tin nhắn với "role" và "content"
            temperature: Tùy chọn ghi đè temperature
            max_tokens: Tùy chọn ghi đè max_tokens
        
        Returns:
            Văn bản phản hồi của trợ lý
        """
        if not self._validate_api_key():
            raise ValueError("DEEPSEEK_API_KEY chưa được cấu hình. Vui lòng đặt trong file .env.")
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature or self.temperature,
                    "max_tokens": max_tokens or self.max_tokens,
                    "stream": False
                }
                
                logger.info(
                    "deepseek.request",
                    model=self.model,
                    messages=len(messages),
                    max_tokens=payload["max_tokens"]
                )
                
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "choices" not in result or not result["choices"]:
                    logger.error("deepseek.invalid_response", response=result)
                    raise ValueError("Phản hồi không hợp lệ từ API DeepSeek")
                
                assistant_message = result["choices"][0]["message"]["content"]
                
                logger.info(
                    "deepseek.response",
                    model=self.model,
                    tokens_used=result.get("usage", {}).get("total_tokens", "unknown")
                )
                
                return assistant_message
        
        except httpx.HTTPStatusError as e:
            logger.error(
                "deepseek.http_error",
                status=e.response.status_code,
                error=e.response.text[:200]
            )
            raise ValueError(f"Lỗi API DeepSeek: {e.response.status_code}")
        
        except Exception as e:
            logger.error("deepseek.error", error=str(e))
            raise


# Global service instance
llm_service = DeepSeekLLMService()
