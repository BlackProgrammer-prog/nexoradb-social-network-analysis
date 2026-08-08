"""Application settings and environment configuration."""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    APP_NAME: str = "NexoraDB Social Graph API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8100

    # NexoraDB Connection
    NEXORADB_URL: str = Field(
        default="http://localhost:8000",
        description="NexoraDB API endpoint URL"
    )
    NEXORADB_APP_TOKEN: str = Field(
        ...,
        description="Application token for authentication",
        min_length=10
    )
    DRIVER_TIMEOUT: float = Field(
        default=15.0,
        description="Timeout for regular queries (seconds)"
    )
    JOB_TIMEOUT: float = Field(
        default=120.0,
        description="Timeout for heavy JOB queries (seconds)"
    )

    # File Upload Limits
    MAX_FILE_SIZE_MB: int = Field(default=10, ge=1, le=100)

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:8501"],
        description="Allowed CORS origins"
    )

    @field_validator("NEXORADB_APP_TOKEN")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate that the token starts with the correct prefix."""
        if not v.startswith("nxapp_"):
            raise ValueError("Token must start with 'nxapp_'")
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate that the environment is one of the allowed values."""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    def validate_for_startup(self) -> None:
        """Perform critical validation before application startup."""
        if self.ENVIRONMENT == "production" and self.DEBUG:
            raise ValueError("DEBUG must be False in production environment")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()