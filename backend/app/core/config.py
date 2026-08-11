"""
Configuration management using Pydantic settings.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql://postgres:Pakistan%2312@localhost:5432/intellistock"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "local-dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # API
    API_HOST: str = "localhost"
    API_PORT: int = 8000

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        # Explicitly set .env file location
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        case_sensitive = True


# Create a global settings instance
settings = Settings()
