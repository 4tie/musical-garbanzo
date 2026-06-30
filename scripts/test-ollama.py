#!/usr/bin/env python3
"""
Test Ollama integration for HER.
Checks Ollama service availability and model configuration.
Does NOT generate trading strategy content.
"""
import sys
import json
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings


def check_ollama_config():
    """Check Ollama configuration."""
    print(f"OLLAMA_BASE_URL: {settings.OLLAMA_BASE_URL}")
    print(f"OLLAMA_MODEL: {settings.OLLAMA_MODEL}")
    
    if not settings.OLLAMA_BASE_URL:
        print("  ✗ Ollama base URL not configured")
        return False
    
    if not settings.OLLAMA_MODEL:
        print("  ⚠ Ollama model not configured (optional)")
    else:
        print(f"  ✓ Ollama model configured: {settings.OLLAMA_MODEL}")
    
    return True


def check_ollama_reachable():
    """Check if Ollama service is reachable."""
    try:
        # Try to list models via Ollama API
        response = httpx.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags",
            timeout=5.0
        )
        
        if response.status_code == 200:
            print(f"  ✓ Ollama service is reachable")
            return True
        else:
            print(f"  ✗ Ollama service returned status {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"  ✗ Cannot connect to Ollama service")
        return False
    except httpx.TimeoutException:
        print(f"  ✗ Connection to Ollama timed out")
        return False
    except Exception as e:
        print(f"  ✗ Error checking Ollama: {e}")
        return False


def get_available_models():
    """Get list of available Ollama models."""
    try:
        response = httpx.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags",
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [model.get("name", "unknown") for model in models]
            return model_names
        return []
    except Exception as e:
        print(f"  ✗ Error fetching models: {e}")
        return []


def check_configured_model_available():
    """Check if the configured model is available."""
    if not settings.OLLAMA_MODEL:
        print("  ℹ No model configured to check")
        return None
    
    available_models = get_available_models()
    
    if not available_models:
        print("  ⚠ Could not fetch available models")
        return None
    
    print(f"  Available models: {', '.join(available_models[:5])}")
    if len(available_models) > 5:
        print(f"  ... and {len(available_models) - 5} more")
    
    # Check if configured model is available
    model_found = any(
        settings.OLLAMA_MODEL in model_name 
        for model_name in available_models
    )
    
    if model_found:
        print(f"  ✓ Configured model '{settings.OLLAMA_MODEL}' is available")
        return True
    else:
        print(f"  ✗ Configured model '{settings.OLLAMA_MODEL}' not found")
        return False


def main():
    """Run all Ollama checks."""
    print("=" * 60)
    print("HER Ollama Integration Check")
    print("=" * 60)
    
    print("\n[Ollama Configuration]")
    configured = check_ollama_config()
    
    print("\n[Ollama Service Reachability]")
    if configured:
        reachable = check_ollama_reachable()
    else:
        reachable = False
        print("  ⚠ Skipping reachability check (not configured)")
    
    print("\n[Model Availability]")
    if reachable:
        model_available = check_configured_model_available()
    else:
        model_available = None
        print("  ⚠ Skipping model check (service not reachable)")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Configured: {configured}")
    print(f"  Service Reachable: {reachable}")
    print(f"  Model Available: {model_available}")
    print("=" * 60)
    
    if not configured:
        print("\n⚠ Ollama is not configured")
        print("   Set OLLAMA_BASE_URL and optionally OLLAMA_MODEL in .env")
        sys.exit(1)
    elif not reachable:
        print("\n⚠ Ollama service is not reachable")
        print("   Ensure Ollama is running: ollama serve")
        sys.exit(1)
    elif model_available is False:
        print("\n⚠ Configured model is not available")
        print(f"   Pull the model: ollama pull {settings.OLLAMA_MODEL}")
        sys.exit(1)
    else:
        print("\n✓ Ollama integration looks good")
        sys.exit(0)


if __name__ == "__main__":
    main()
