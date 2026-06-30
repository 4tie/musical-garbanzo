#!/usr/bin/env python3
"""
Test Freqtrade integration for HER.
Checks Freqtrade configuration, executable, and workspace structure.
Does NOT run trading, backtests, or download data.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.freqtrade_detection import FreqtradeDetectionService
from app.services.freqtrade_workspace import FreqtradeWorkspaceService


def main():
    """Run all Freqtrade checks."""
    print("=" * 60)
    print("HER Freqtrade Integration Check")
    print("=" * 60)
    
    workspace_service = FreqtradeWorkspaceService()
    detection_service = FreqtradeDetectionService(workspace_service=workspace_service)

    status = detection_service.get_status()
    workspace = status.workspace or workspace_service.validate_workspace()

    print("\n[Freqtrade Detection]")
    print(f"  configured: {status.configured}")
    print(f"  path source: {status.path_source}")
    print(f"  executable path: {status.executable_path or 'not found'}")
    print(f"  executable available: {status.executable_available}")
    print(f"  version: {status.version or 'unavailable'}")
    if status.error:
        print(f"  version check: {status.error}")

    print("\n[Workspace Validation]")
    print(f"  user data dir: {workspace.user_data_dir}")
    print(f"  config dir: {workspace.config_dir}")
    print(f"  workspace valid: {workspace.valid}")
    print(f"  missing dirs: {', '.join(workspace.missing_dirs) if workspace.missing_dirs else 'none'}")
    print(f"  created dirs: {', '.join(workspace.created_dirs) if workspace.created_dirs else 'none'}")

    for directory in workspace.directories:
        marker = "ok" if directory.exists and directory.is_dir and directory.writable else "needs attention"
        print(f"  - {directory.key}: {marker} ({directory.path})")

    action_required = status.user_action_required or workspace.user_action_required or "none"
    print("\n[User Action Required]")
    print(f"  {action_required}")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Configured: {status.configured}")
    print(f"  Executable Available: {status.executable_available}")
    print(f"  Version Available: {bool(status.version)}")
    print(f"  Workspace Valid: {workspace.valid}")
    print("=" * 60)

    if status.executable_available and workspace.valid:
        print("\nFreqtrade detection and workspace validation look ready.")
    else:
        print("\nFreqtrade integration is not ready yet; see user action above.")

    # This script is a diagnostic. Missing Freqtrade is a controlled status,
    # not a script crash or fake readiness success.
    sys.exit(0)


if __name__ == "__main__":
    main()
