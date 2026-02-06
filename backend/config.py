from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path

# Get the directory where this config file lives
CONFIG_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # Database
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "student_hub"
    
    # Redis
    redis_host: str = "redis-10898.c232.us-east-1-2.ec2.cloud.redislabs.com"
    redis_port: int = 10898
    redis_username: str = "default"
    redis_password: Optional[str] = "WsixNP6MHjEJJ0p27Kzrs2CCBj1roH2G"
    redis_db: int = 0
    redis_ssl: bool = False
    
    # Authentication
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    
    # Frontend
    frontend_origin: str = "http://localhost:5173"
    frontend_base_url: Optional[str] = None
    
    # Environment
    app_env: str = "development"
    
    # Email (SMTP - Gmail)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: Optional[str] = None
    sender_password: Optional[str] = None
    email_from: Optional[str] = None
    password_reset_token_expires_minutes: int = 60
    password_min_length: int = 8
    
    # AI Services - OpenRouter (Default)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "tngtech/deepseek-r1t-chimera:free"
    
    # AI Services - Gemini
    google_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    
    # AI Services - Tavily (Research/Search)
    tavily_api_key: Optional[str] = None
    
    # AI Services - OpenAI (Optional)
    openai_api_key: Optional[str] = None
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_ai: str = "10/minute"
    rate_limit_auth: str = "5/minute"

    class Config:
        env_file = str(CONFIG_DIR / ".env")
        env_file_encoding = "utf-8"

    @property
    def frontend_origins(self) -> List[str]:
        """Return list of allowed frontend origins for CORS."""
        origins = [
            # Local development
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            # Vercel production (add your actual Vercel URLs)
            "https://studenthub.vercel.app",
            "https://student-hub.vercel.app",
            "https://studenthub-frontend.vercel.app",
        ]
        # Add custom frontend origin from env if set
        if self.frontend_origin and self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        return origins


settings = Settings()
