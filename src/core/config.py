from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # OpenAI Configuration
    openai_api_key: str
    
    # LiveKit Configuration
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    
    # Database Configuration
    database_path: str = "salon_data.db"
    
    # Help Request Configuration
    help_request_timeout_hours: int = 24
    
    # Application Configuration
    app_name: str = "Salon AI Supervisor"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Validation on import
if not settings.openai_api_key:
    raise ValueError("OPENAI_API_KEY not set in environment")

if not all([settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret]):
    raise ValueError("LiveKit credentials not set in environment")