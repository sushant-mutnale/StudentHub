from pydantic_settings import BaseSettings
from pydantic import model_validator, Field
from typing import List, Optional
from pathlib import Path

# Get the directory where this config file lives
CONFIG_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # Database
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "student_hub"
    
    # Redis (MUST be set in .env)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_username: str = "default"
    redis_password: Optional[str] = None  # Loaded from .env
    redis_db: int = 0
    redis_ssl: bool = False
    
    # Authentication (MUST be set in .env for production)
    jwt_secret: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    
    # Frontend
    frontend_origin: str = "http://localhost:5173"
    frontend_base_url: Optional[str] = None
    # Comma-separated extra origins injected via env (e.g. FRONTEND_ORIGINS=https://a.com,https://b.com)
    frontend_origins_extra: Optional[str] = None
    frontend_origins_env: Optional[str] = Field(default=None, validation_alias="FRONTEND_ORIGINS")
    
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
    
    # AI Services - Provider Selection
    llm_provider: str = "openrouter"
    llm_model: Optional[str] = None
    
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
    
    # AI Services - Pinecone (Memory/RAG)
    pinecone_api_key: Optional[str] = None
    pinecone_index: str = "studenthub"

    # Scrapers
    apify_api_key: Optional[str] = None
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_ai: str = "10/minute"
    rate_limit_auth: str = "5/minute"

    class Config:
        env_file = str(CONFIG_DIR / ".env")
        env_file_encoding = "utf-8"
        env_prefix = ""

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Enforce that production deployments use a real JWT secret."""
        if (
            self.app_env == "production"
            and self.jwt_secret == "dev-only-change-me-in-production"
        ):
            raise ValueError(
                "JWT_SECRET must be changed from the default value in production. "
                "Set a strong random secret in your environment variables."
            )
        return self

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
            # Vercel production
            "https://studenthub.vercel.app",
            "https://student-hub.vercel.app",
            "https://studenthub-frontend.vercel.app",
            "https://studenthub-five-self.vercel.app",
            "https://studenthub-five-self.vercel.app/",
            "https://student-hub-five-self.vercel.app",
            "https://student-hub-five-self.vercel.app/",
        ]
        # Add single custom frontend origin from env if set
        if self.frontend_origin and self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        # Add comma-separated FRONTEND_ORIGINS env var entries
        if self.frontend_origins_extra:
            for origin in self.frontend_origins_extra.split(","):
                origin = origin.strip()
                if origin and origin not in origins:
                    origins.append(origin)
        if self.frontend_origins_env:
            for origin in self.frontend_origins_env.split(","):
                origin = origin.strip()
                if origin and origin not in origins:
                    origins.append(origin)
        return origins


settings = Settings()
