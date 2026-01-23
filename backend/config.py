from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "student_hub"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    frontend_origin: str = "http://localhost:5173"
    frontend_base_url: str | None = None
    app_env: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def frontend_origins(self) -> List[str]:
        """Return list of allowed frontend origins for CORS."""
        # Allow both localhost and 127.0.0.1 variants for local development
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        # If custom origin is set and not in list, add it
        if self.frontend_origin and self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        return origins


settings = Settings()


