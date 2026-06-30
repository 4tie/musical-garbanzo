#!/usr/bin/env python3
"""
Check HER system configuration and dependencies.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.sqlite import database_exists, get_database_path


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 12:
        print("  ✓ Python version OK")
        return True
    else:
        print("  ✗ Python version should be 3.12+")
        return False


def check_project_root():
    """Check project root exists."""
    print(f"Project root: {settings.project_root}")
    if settings.project_root.exists():
        print("  ✓ Project root exists")
        return True
    else:
        print("  ✗ Project root not found")
        return False


def check_docs():
    """Check docs directory exists."""
    docs_path = settings.project_root / "docs"
    print(f"Docs path: {docs_path}")
    if docs_path.exists() and docs_path.is_dir():
        print("  ✓ Docs directory exists")
        return True
    else:
        print("  ✗ Docs directory not found")
        return False


def check_env_files():
    """Check .env.example and .env files."""
    project_root = settings.project_root
    env_example = project_root / ".env.example"
    env_file = project_root / ".env"
    
    print(f".env.example: {env_example}")
    if env_example.exists():
        print("  ✓ .env.example exists")
    else:
        print("  ✗ .env.example not found")
    
    print(f".env: {env_file}")
    if env_file.exists():
        print("  ✓ .env exists")
    else:
        print("  ⚠ .env not found (using defaults)")


def check_database():
    """Check database exists or can be created."""
    db_path = get_database_path()
    print(f"Database path: {db_path}")
    
    if database_exists():
        print("  ✓ Database exists")
        return True
    else:
        print("  ⚠ Database does not exist (will be created on startup)")
        return True  # Not a failure, will be created


def check_backend_import():
    """Check backend can be imported."""
    try:
        from app.main import app
        print("  ✓ Backend import successful")
        return True
    except Exception as e:
        print(f"  ✗ Backend import failed: {e}")
        return False


def check_freqtrade():
    """Check Freqtrade configuration."""
    print(f"Freqtrade path: {settings.FREQTRADE_PATH}")
    print(f"Freqtrade configured: {settings.freqtrade_configured}")
    
    if settings.freqtrade_configured:
        print("  ✓ Freqtrade configured")
        return True
    else:
        print("  ⚠ Freqtrade not configured")
        return False


def check_ollama():
    """Check Ollama configuration."""
    print(f"Ollama base URL: {settings.OLLAMA_BASE_URL}")
    print(f"Ollama model: {settings.OLLAMA_MODEL}")
    print(f"Ollama configured: {settings.ollama_configured}")
    
    if settings.ollama_configured:
        print("  ✓ Ollama configured")
        return True
    else:
        print("  ⚠ Ollama not configured")
        return False


def check_discord():
    """Check Discord configuration."""
    print(f"Discord enabled: {settings.discord_enabled}")
    print(f"Discord channel configured: {settings.discord_channel_configured}")
    
    if settings.discord_enabled:
        if settings.discord_channel_configured:
            print("  ✓ Discord configured")
        else:
            print("  ⚠ Discord enabled but channel not configured")
    else:
        print("  ℹ Discord disabled")
    
    # Never print the token
    if settings.DISCORD_BOT_TOKEN:
        print("  ℹ Discord bot token is set (hidden)")


def main():
    """Run all system checks."""
    print("=" * 60)
    print("HER System Check")
    print("=" * 60)
    
    print("\n[Python]")
    check_python_version()
    
    print("\n[Project Structure]")
    check_project_root()
    check_docs()
    
    print("\n[Environment]")
    check_env_files()
    
    print("\n[Database]")
    check_database()
    
    print("\n[Backend]")
    check_backend_import()
    
    print("\n[Integrations]")
    check_freqtrade()
    check_ollama()
    check_discord()
    
    print("\n" + "=" * 60)
    print("System check complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
