"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings."""
    
    APP_NAME: str = "Chatbot"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = APP_ENV == "development"
    
    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./chatbot.db"
    
    # Google Sheets settings
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "credentials.json"
    GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
    SHEET_CUSTOMERS_ID: str = os.getenv("SHEET_CUSTOMERS_ID", "")
    SHEET_PRODUCTS_ID: str = os.getenv("SHEET_PRODUCTS_ID", "")
    SHEET_FAQ_ID: str = os.getenv("SHEET_FAQ_ID", "")
    SHEET_LOGS_ID: str = os.getenv("SHEET_LOGS_ID", "")
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    
        # Chroma settings
    CHROMA_COLLECTION_NAME: str = "chatbot_documents"
    
    # System prompt for LLM
    SYSTEM_PROMPT: str = "Bạn là một trợ lý AI hữu ích. Luôn trả lời bằng tiếng Việt một cách thân thiện và chuyên nghiệp. Toàn bộ câu trả lời của bạn PHẢI được viết bằng tiếng Việt."
    
    # DeepSeek API settings
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TEMPERATURE: float = 0.7
    DEEPSEEK_MAX_TOKENS: int = 1000
    
    # Google Sheets auto-sync interval (seconds)
    SHEETS_SYNC_INTERVAL: int = 300
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
