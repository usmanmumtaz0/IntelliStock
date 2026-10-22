"""Validated application configuration loaded exclusively from the environment."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILES = (BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_ENV: Literal["development", "test", "production"] = "development"
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SOCKET_TIMEOUT_SECONDS: float = Field(default=1.0, gt=0, le=30)

    JWT_SECRET: SecretStr
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = Field(default=8, ge=1, le=24)

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]

    LOG_LEVEL: str = "INFO"
    TRUSTED_PROXY_HEADERS: bool = False

    RATE_LIMIT_LOGIN_REQUESTS: int = Field(default=5, ge=1, le=100)
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = Field(default=60, ge=1, le=3600)
    RATE_LIMIT_DEFAULT_REQUESTS: int = Field(default=100, ge=1)
    RATE_LIMIT_DEFAULT_WINDOW_SECONDS: int = Field(default=60, ge=1)

    # Per-process budget: leave room for migrations and other services on small poolers.
    DATABASE_POOL_SIZE: int = Field(default=3, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=2, ge=0, le=200)
    ALERT_COOLDOWN_SECONDS: int = Field(default=300, ge=0)
    ALERT_ESCALATION_SECONDS: int = Field(default=900, ge=60)
    CV_MODEL_PATH: str = ""
    CV_MODEL_MANIFEST: str = ""
    CV_DETECTOR: Literal["yolov8"] = "yolov8"
    CV_DEVICE: str = "auto"
    CV_CONFIDENCE_THRESHOLD: float = Field(default=0.40, ge=0.01, le=1.0)
    CV_IMAGE_SIZE: int = Field(default=640, ge=320, le=1920)
    CV_NMS_IOU_THRESHOLD: float = Field(default=0.45, ge=0.01, le=1.0)
    CV_MAX_DETECTIONS: int = Field(default=300, ge=1, le=5000)
    CV_IDENTITY_MIN_CONFIDENCE: float = Field(default=0.65, ge=0.01, le=1.0)
    CV_OCR_ENABLED: bool = False
    CV_OCR_LANGUAGE: str = "en"
    CV_OCR_VERSION: str = "PP-OCRv6"
    CV_OCR_DEVICE: str = "cpu"
    CV_OCR_MIN_CONFIDENCE: float = Field(default=0.55, ge=0.0, le=1.0)
    CV_OCR_MATCH_MIN_CONFIDENCE: float = Field(default=0.72, ge=0.0, le=1.0)
    CV_OCR_MATCH_MIN_MARGIN: float = Field(default=0.10, ge=0.0, le=1.0)
    CV_FLORENCE_ENABLED: bool = False
    CV_FLORENCE_MODEL_ID: str = "microsoft/Florence-2-base"
    CV_FLORENCE_MODEL_PATH: str = ""
    CV_FLORENCE_ALLOW_REMOTE_DOWNLOAD: bool = False
    CV_FLORENCE_TRUST_REMOTE_CODE: bool = False
    CV_FLORENCE_DEVICE: str = "cpu"
    CV_FLORENCE_TASK: Literal["<CAPTION>", "<DETAILED_CAPTION>", "<MORE_DETAILED_CAPTION>"] = "<DETAILED_CAPTION>"
    CV_FLORENCE_POLICY: Literal["ambiguous", "low_confidence", "ambiguous_or_low_confidence"] = "ambiguous_or_low_confidence"
    CV_FLORENCE_TRIGGER_MAX_CONFIDENCE: float = Field(default=0.70, ge=0.0, le=1.0)
    CV_FLORENCE_MATCH_MIN_CONFIDENCE: float = Field(default=0.72, ge=0.0, le=1.0)
    CV_FLORENCE_MATCH_MIN_MARGIN: float = Field(default=0.10, ge=0.0, le=1.0)
    CV_FLORENCE_MAX_NEW_TOKENS: int = Field(default=128, ge=16, le=1024)
    CV_FLORENCE_NUM_BEAMS: int = Field(default=3, ge=1, le=8)
    CV_EMBEDDING_ENABLED: bool = False
    CV_EMBEDDING_MODEL_PATH: str = ""
    CV_EMBEDDING_DEVICE: str = "cpu"
    CV_REFERENCE_IMAGE_ROOT: str = str(BACKEND_DIR / "media" / "product-references")
    CV_RETRIEVAL_MIN_CONFIDENCE: float = Field(default=0.82, ge=-1.0, le=1.0)
    CV_RETRIEVAL_MIN_MARGIN: float = Field(default=0.05, ge=0.0, le=2.0)
    CV_MAX_REFERENCE_IMAGES: int = Field(default=500, ge=1, le=10000)
    CV_EVIDENCE_REFRESH_SHARPNESS_RATIO: float = Field(default=1.20, ge=1.0, le=10.0)
    CV_IDENTITY_CACHE_ROOT: str = str(BACKEND_DIR / "media" / "model-cache")
    VIDEO_STORAGE_ROOT: str = str(BACKEND_DIR / "media" / "video-jobs")
    VIDEO_MAX_UPLOAD_BYTES: int = Field(default=500 * 1024 * 1024, ge=1024 * 1024)
    IMAGE_MAX_UPLOAD_BYTES: int = Field(default=25 * 1024 * 1024, ge=1024 * 1024)
    VIDEO_MAX_FRAMES: int = Field(default=300, ge=1, le=10000)
    VIDEO_MAX_DURATION_SECONDS: int = Field(default=900, ge=1, le=86400)
    VIDEO_PREVIEW_FRAMES: int = Field(default=12, ge=1, le=100)
    VIDEO_WORKER_POLL_SECONDS: float = Field(default=1.0, ge=0.1, le=30)
    VIDEO_ALLOWED_CAMERA_HOSTS: str = ""

    # Credentials never enable outbound delivery by themselves.
    # AI routing defaults to local; SMTP requires explicit opt-in; SMS is reserved.
    OPENAI_API_KEY: SecretStr | None = None
    OPENROUTER_API_KEY: SecretStr | None = None
    CHAT_PROVIDER: Literal["local", "openai", "openrouter"] = "local"
    CHAT_MODEL: str = Field(default="", max_length=100)
    CHAT_TIMEOUT_SECONDS: float = Field(default=15, gt=0, le=30)
    CHAT_MAX_TURNS: int = Field(default=100, ge=1, le=200)
    CHAT_REQUESTS_PER_MINUTE: int = Field(default=10, ge=1, le=60)
    SMTP_PASSWORD: SecretStr | None = None
    NOTIFICATIONS_ENABLED: bool = False
    NOTIFICATION_EMAIL_TO: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_USERNAME: str = ""
    SMTP_FROM: str = ""
    SMTP_SECURITY: Literal["starttls", "ssl"] = "starttls"
    SMTP_TIMEOUT_SECONDS: float = Field(default=10, gt=0, le=30)
    NOTIFICATION_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=10)
    TWILIO_AUTH_TOKEN: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Reject unsafe or incompatible runtime configuration."""
        secret = self.JWT_SECRET.get_secret_value()
        normalized_secret = secret.lower()
        if (
            len(secret) < 32
            or "replace" in normalized_secret
            or "secret-key" in normalized_secret
        ):
            raise ValueError("JWT_SECRET must be a non-placeholder value of at least 32 characters")

        if self.JWT_ALGORITHM not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be an approved HMAC algorithm")

        if self.APP_ENV != "test" and not self.DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must use PostgreSQL outside the test environment")
        if self.APP_ENV == "production" and "replace_locally" in self.DATABASE_URL:
            raise ValueError("DATABASE_URL still contains a placeholder")
        return self


settings = Settings()
