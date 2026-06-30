"""
Configuration settings for HER backend using environment variables.
"""
from pathlib import Path
import shutil
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Basic App Settings
    APP_NAME: str = "HER"
    APP_ENV: str = "local"
    APP_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000

    # Database
    DATABASE_URL: str = "sqlite:///./data/her.db"

    # Freqtrade Configuration
    FREQTRADE_PATH: Optional[str] = None
    FREQTRADE_USER_DATA_DIR: str = "./freqtrade_workspace/user_data"
    FREQTRADE_CONFIG_DIR: str = "./freqtrade_workspace/config"
    FREQTRADE_DEFAULT_CONFIG: str = "./freqtrade_workspace/config/config.generated.json"
    FREQTRADE_DEFAULT_EXCHANGE: str = "binance"
    FREQTRADE_DEFAULT_TRADING_MODE: str = "spot"
    FREQTRADE_DEFAULT_STAKE_CURRENCY: str = "USDT"
    FREQTRADE_DEFAULT_TIMEFRAME: str = "5m"
    FREQTRADE_REAL_SMOKE_ENABLED: bool = False

    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: Optional[str] = None

    # Discord Configuration
    DISCORD_NOTIFICATIONS_ENABLED: bool = False
    DISCORD_CHANNEL_ID: Optional[str] = None
    DISCORD_BOT_TOKEN: Optional[SecretStr] = Field(default=None, exclude=True)

    # Security
    APP_SECRET_KEY: str = "change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent.parent

    @property
    def freqtrade_user_data_dir_path(self) -> Path:
        """Get the absolute path to Freqtrade user data directory."""
        return self.project_root / self.FREQTRADE_USER_DATA_DIR

    @property
    def freqtrade_config_dir_path(self) -> Path:
        """Get the absolute path to Freqtrade config directory."""
        return self.project_root / self.FREQTRADE_CONFIG_DIR

    @property
    def freqtrade_default_config_path(self) -> Path:
        """Get the absolute path to Freqtrade default config file."""
        return self.project_root / self.FREQTRADE_DEFAULT_CONFIG

    @property
    def freqtrade_configured(self) -> bool:
        """Check if Freqtrade is configured."""
        if self.FREQTRADE_PATH:
            return True
        if shutil.which("freqtrade"):
            return True
        return self.freqtrade_default_config_path.exists()

    @property
    def ollama_configured(self) -> bool:
        """Check if Ollama is configured."""
        return bool(self.OLLAMA_MODEL)

    @property
    def discord_enabled(self) -> bool:
        """Check if Discord notifications are enabled."""
        return self.DISCORD_NOTIFICATIONS_ENABLED

    @property
    def discord_channel_configured(self) -> bool:
        """Check if Discord channel is configured."""
        return bool(self.DISCORD_CHANNEL_ID)


settings = Settings()
