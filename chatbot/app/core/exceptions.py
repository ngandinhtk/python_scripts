"""Custom exceptions for the chatbot."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Optional


class ChatbotException(Exception):
    """Base exception for chatbot errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


async def chatbot_exception_handler(request: Request, exc: ChatbotException):
    """Handle ChatbotException globally."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": exc.message}
    )
