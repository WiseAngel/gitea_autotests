"""
Configuration settings for the Playwright QA Framework.

Uses pydantic-settings for strict validation at import time.
All settings are loaded from .env file or environment variables.
"""

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with validation.

    Attributes:
        base_url: Base URL of the application under test
        api_base_url: Base URL for API requests (defaults to base_url + /api/v1)
        db_host: Database host
        db_port: Database port
        db_name: Database name
        db_user: Database user
        db_password: Database password
        api_token: API authentication token
        headless: Run browsers in headless mode
        browser: Browser to use (chromium, firefox, webkit)
        timeout: Default timeout for operations in milliseconds
        slow_mo: Slow down operations by this many milliseconds
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # Application
    base_url: str = "https://gitea.com"
    api_base_url: str | None = None
    headless: bool = True
    browser: str = "chromium"
    timeout: int = 30000
    slow_mo: int = 0
    gitea_username: str = ""
    gitea_password: str = ""

    @field_validator("base_url", mode="before")
    @classmethod
    def set_default_base_url(cls, v: str) -> str:
        """Set default base_url if empty or not provided."""
        if not v:
            return "https://gitea.com"
        return v

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "qa_test"
    db_user: str = "qa"
    db_password: str = "qa_pass"

    # Authentication
    api_token: str = ""

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base_url starts with http:// or https://."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("api_base_url")
    @classmethod
    def validate_api_url(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate api_base_url or derive from base_url."""
        if v is None:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("api_base_url must start with http:// or https://")
        return v.rstrip("/")

    @property
    def db_url(self) -> str:
        """Construct database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def effective_api_url(self) -> str:
        """Get effective API URL (derived from base_url if not set)."""
        if self.api_base_url:
            return self.api_base_url
        return f"{self.base_url}/api/v1"


# Global settings instance
settings = Settings()
