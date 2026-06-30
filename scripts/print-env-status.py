#!/usr/bin/env python3
"""
Print environment configuration status for HER.
Displays configured/missing flags without exposing actual secret values.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings


def print_env_status():
    """Print environment configuration status safely."""
    print("=" * 60)
    print("HER Environment Configuration Status")
    print("=" * 60)
    
    print("\n[Application Settings]")
    print(f"  APP_NAME: {settings.APP_NAME}")
    print(f"  APP_ENV: {settings.APP_ENV}")
    print(f"  APP_HOST: {settings.APP_HOST}")
    print(f"  BACKEND_PORT: {settings.BACKEND_PORT}")
    print(f"  FRONTEND_PORT: {settings.FRONTEND_PORT}")
    
    print("\n[Database]")
    print(f"  DATABASE_URL: {settings.DATABASE_URL}")
    
    print("\n[Freqtrade Configuration]")
    print(f"  FREQTRADE_PATH: {'***CONFIGURED***' if settings.FREQTRADE_PATH else 'NOT SET'}")
    print(f"  FREQTRADE_USER_DATA_DIR: {settings.FREQTRADE_USER_DATA_DIR}")
    print(f"  FREQTRADE_CONFIG_DIR: {settings.FREQTRADE_CONFIG_DIR}")
    print(f"  FREQTRADE_DEFAULT_CONFIG: {settings.FREQTRADE_DEFAULT_CONFIG}")
    print(f"  Freqtrade Configured: {settings.freqtrade_configured}")
    
    print("\n[Ollama Configuration]")
    print(f"  OLLAMA_BASE_URL: {settings.OLLAMA_BASE_URL}")
    print(f"  OLLAMA_MODEL: {'***CONFIGURED***' if settings.OLLAMA_MODEL else 'NOT SET'}")
    print(f"  Ollama Configured: {settings.ollama_configured}")
    
    print("\n[Discord Configuration]")
    print(f"  DISCORD_NOTIFICATIONS_ENABLED: {settings.DISCORD_NOTIFICATIONS_ENABLED}")
    print(f"  DISCORD_CHANNEL_ID: {'***CONFIGURED***' if settings.DISCORD_CHANNEL_ID else 'NOT SET'}")
    print(f"  DISCORD_BOT_TOKEN: {'***CONFIGURED***' if settings.DISCORD_BOT_TOKEN else 'NOT SET'}")
    print(f"  Discord Enabled: {settings.discord_enabled}")
    print(f"  Discord Channel Configured: {settings.discord_channel_configured}")
    
    print("\n[Security]")
    print(f"  APP_SECRET_KEY: {'***CONFIGURED***' if settings.APP_SECRET_KEY != 'change-me' else 'DEFAULT (CHANGE IN PRODUCTION)'}")
    
    print("\n[Paths]")
    print(f"  Project Root: {settings.project_root}")
    print(f"  Freqtrade User Data: {settings.freqtrade_user_data_dir_path}")
    print(f"  Freqtrade Config: {settings.freqtrade_config_dir_path}")
    
    print("\n" + "=" * 60)
    print("Configuration Summary")
    print("=" * 60)
    
    configured_count = 0
    total_count = 0
    
    # Check key configurations
    checks = [
        ("Freqtrade", settings.freqtrade_configured),
        ("Ollama", settings.ollama_configured),
        ("Discord", settings.discord_enabled),
    ]
    
    for name, configured in checks:
        total_count += 1
        if configured:
            configured_count += 1
            print(f"  ✓ {name}: Configured")
        else:
            print(f"  ⚠ {name}: Not configured")
    
    print(f"\n  Integrations Configured: {configured_count}/{total_count}")
    
    if configured_count == 0:
        print("\n  ℹ No integrations configured. See .env.example for setup instructions.")
    elif configured_count < total_count:
        print("\n  ℹ Some integrations not configured. See .env.example for setup instructions.")
    else:
        print("\n  ✓ All integrations configured.")
    
    print("=" * 60)


if __name__ == "__main__":
    print_env_status()
