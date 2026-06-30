"""
Safety tests for the Freqtrade real smoke script and strategy.

These tests verify that the smoke script and strategy adhere to safety rules:
- No live trading commands
- No webserver commands
- No --erase flag
- No exchange keys
- No Ollama calls
- No Discord messages
- Proper warning comments in strategy
"""
import pytest
from pathlib import Path
import re


def extract_code_only(content: str) -> str:
    """
    Extract only executable code, excluding comments and docstrings.
    """
    lines = content.split('\n')
    code_lines = []
    in_docstring = False
    docstring_delimiter = None
    
    for line in lines:
        stripped = line.strip()
        
        # Track docstring state
        if '"""' in line:
            if not in_docstring:
                in_docstring = True
                docstring_delimiter = '"""'
                continue
            elif in_docstring and docstring_delimiter == '"""':
                # Check if this closes the docstring
                if line.count('"""') >= 2 or (stripped.endswith('"""') and '"""' not in stripped[:-3]):
                    in_docstring = False
                    docstring_delimiter = None
                    continue
        elif "'''" in line:
            if not in_docstring:
                in_docstring = True
                docstring_delimiter = "'''"
                continue
            elif in_docstring and docstring_delimiter == "'''":
                if line.count("'''") >= 2 or (stripped.endswith("'''") and "'''" not in stripped[:-3]):
                    in_docstring = False
                    docstring_delimiter = None
                    continue
        
        # Skip if in docstring
        if in_docstring:
            continue
        
        # Skip comments
        if stripped.startswith('#'):
            continue
        
        code_lines.append(line)
    
    return '\n'.join(code_lines)


# Paths to safety-critical files
SMOKE_SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "freqtrade-real-smoke-test.py"
SMOKE_STRATEGY_PATH = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERSmokeStrategy.py"
SMOKE_JSON_PATH = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERSmokeStrategy.json"


def test_smoke_script_exists():
    """Test that the smoke script file exists."""
    assert SMOKE_SCRIPT_PATH.exists(), f"Smoke script not found at {SMOKE_SCRIPT_PATH}"


def test_smoke_strategy_exists():
    """Test that the smoke strategy file exists."""
    assert SMOKE_STRATEGY_PATH.exists(), f"Smoke strategy not found at {SMOKE_STRATEGY_PATH}"


def test_smoke_json_exists():
    """Test that the smoke strategy JSON file exists."""
    assert SMOKE_JSON_PATH.exists(), f"Smoke strategy JSON not found at {SMOKE_JSON_PATH}"


def test_smoke_strategy_contains_warning_comments():
    """Test that the smoke strategy contains required warning comments."""
    content = SMOKE_STRATEGY_PATH.read_text()
    
    required_warnings = [
        "SMOKE TEST",
        "NOT a profitable strategy",
        "NOT a production strategy",
        "NOT financial advice"
    ]
    
    for warning in required_warnings:
        assert warning in content, f"Missing required warning: '{warning}'"


def test_smoke_script_does_not_contain_trade_command():
    """Test that the smoke script does not execute trade command."""
    content = SMOKE_SCRIPT_PATH.read_text()
    code_only = extract_code_only(content)
    
    # Check for actual command execution patterns
    dangerous_patterns = [
        r"subprocess\..*trade",
        r"run_command\(.*['\"].*trade.*['\"]",
        r"FreqtradeCommandRunner.*trade",
    ]
    
    for pattern in dangerous_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), \
            f"Found dangerous trade execution pattern: {pattern}"


def test_smoke_script_does_not_contain_webserver():
    """Test that the smoke script does not execute webserver command."""
    content = SMOKE_SCRIPT_PATH.read_text()
    code_only = extract_code_only(content)
    
    # Check for actual command execution patterns
    dangerous_patterns = [
        r"subprocess\..*webserver",
        r"run_command\(.*['\"].*webserver.*['\"]",
    ]
    
    for pattern in dangerous_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), \
            f"Found dangerous webserver execution pattern: {pattern}"


def test_smoke_script_does_not_contain_erase_flag():
    """Test that the smoke script does not use --erase flag in commands."""
    content = SMOKE_SCRIPT_PATH.read_text()
    code_only = extract_code_only(content)
    
    # Check for --erase in command execution contexts
    dangerous_patterns = [
        r"subprocess\..*--erase",
        r"run_command\(.*--erase",
        r"command.*=.*\[.*--erase",
    ]
    
    for pattern in dangerous_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), \
            f"Found dangerous --erase flag pattern: {pattern}"


def test_smoke_script_references_download_data():
    """Test that the smoke script references download-data."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    assert "download-data" in content or "download_data" in content, \
        "Smoke script should reference download-data"


def test_smoke_script_references_backtesting():
    """Test that the smoke script references backtesting."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    assert "backtesting" in content or "backtest" in content, \
        "Smoke script should reference backtesting"


def test_smoke_script_requires_freqtrade_real_availability():
    """Test that the smoke script checks for real Freqtrade availability."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    # Should check for Freqtrade configuration
    assert "FreqtradeDetectionService" in content or "get_status" in content or \
           "configured" in content, \
        "Smoke script should check for Freqtrade availability"
    
    # Should exit clearly if not configured
    assert "REAL_SMOKE_PENDING" in content or "not configured" in content, \
        "Smoke script should exit clearly if Freqtrade not configured"


def test_smoke_script_does_not_call_ollama():
    """Test that the smoke script does not import or call Ollama."""
    content = SMOKE_SCRIPT_PATH.read_text()
    code_only = extract_code_only(content)
    
    # Check for Ollama imports or API calls
    dangerous_patterns = [
        r"import.*ollama",
        r"from.*ollama",
        r"ollama\.",
    ]
    
    for pattern in dangerous_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), \
            f"Found Ollama import/call pattern: {pattern}"


def test_smoke_script_does_not_call_discord():
    """Test that the smoke script does not import or call Discord."""
    content = SMOKE_SCRIPT_PATH.read_text()
    code_only = extract_code_only(content)
    
    # Check for Discord imports or API calls
    dangerous_patterns = [
        r"import.*discord",
        r"from.*discord",
        r"discord\.",
    ]
    
    for pattern in dangerous_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), \
            f"Found Discord import/call pattern: {pattern}"


def test_smoke_script_does_not_use_exchange_keys():
    """Test that the smoke script does not use exchange keys."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    forbidden_patterns = [
        "api_key",
        "api-key",
        "apikey",
        "secret",
        "exchange_key",
        "exchange-key",
    ]
    
    for pattern in forbidden_patterns:
        # Allow in comments or in "no secrets" context
        lines_with_pattern = [line for line in content.split('\n') if pattern in line]
        for line in lines_with_pattern:
            # Check if it's actually setting a key (not just a comment)
            if "=" in line and "#" not in line.split("=")[0]:
                assert False, f"Found exchange key pattern: {line.strip()}"


def test_smoke_strategy_is_simple():
    """Test that the smoke strategy is simple (no complex dependencies)."""
    content = SMOKE_STRATEGY_PATH.read_text()
    
    # Should not import complex ML libraries
    forbidden_imports = [
        "tensorflow",
        "torch",
        "sklearn",
        "scikit-learn",
        "xgboost",
        "lightgbm",
    ]
    
    for imp in forbidden_imports:
        assert imp not in content, f"Smoke strategy should not import {imp}"


def test_smoke_strategy_uses_dry_run():
    """Test that the smoke strategy sets dry_run to True."""
    content = SMOKE_STRATEGY_PATH.read_text()
    
    assert "dry_run" in content, "Smoke strategy should have dry_run setting"
    assert "dry_run = True" in content or "dry_run=True" in content, \
        "Smoke strategy should set dry_run to True"


def test_smoke_json_contains_warning():
    """Test that the smoke strategy JSON contains warning."""
    content = SMOKE_JSON_PATH.read_text()
    
    assert "warning" in content.lower() or "smoke" in content.lower(), \
        "Smoke strategy JSON should contain warning or smoke reference"
    assert "do_not_use_for_trading" in content or "not_for_trading" in content, \
        "Smoke strategy JSON should indicate it's not for trading"


def test_smoke_json_no_secrets():
    """Test that the smoke strategy JSON does not contain secrets."""
    content = SMOKE_JSON_PATH.read_text()
    
    forbidden_patterns = [
        "api_key",
        "secret",
        "password",
        "token",
    ]
    
    for pattern in forbidden_patterns:
        assert pattern not in content.lower(), f"JSON should not contain {pattern}"


def test_smoke_script_exits_clearly_on_failure():
    """Test that the smoke script has clear exit codes for failures."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    # Should have sys.exit calls with different codes
    assert "sys.exit" in content, "Smoke script should use sys.exit for clear exit codes"
    
    # Should have exit code 1 for Freqtrade not configured
    assert "sys.exit(1)" in content or "exit(1)" in content, \
        "Should have exit code 1 for Freqtrade not configured"
    
    # Should have exit code for data download failure
    assert "sys.exit(3)" in content or "exit(3)" in content, \
        "Should have exit code for data download failure"


def test_smoke_script_creates_her_run():
    """Test that the smoke script creates a HER run record."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    assert "RunRepository" in content, "Should use RunRepository"
    assert "RunCreate" in content, "Should use RunCreate schema"
    assert "create(" in content or "run_repo.create" in content, \
        "Should create a run record"


def test_smoke_script_registers_artifacts():
    """Test that the smoke script registers artifacts."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    assert "ArtifactRepository" in content, "Should use ArtifactRepository"
    assert "artifact_repo.create" in content or "register" in content, \
        "Should register artifacts"


def test_smoke_script_logs_actions():
    """Test that the smoke script logs actions."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    assert "RunLogRepository" in content, "Should use RunLogRepository"
    assert "log_repo.create" in content, "Should log actions"


def test_smoke_script_uses_hersmokestrategy():
    """Test that the smoke script uses HERSmokeStrategy."""
    content = SMOKE_SCRIPT_PATH.read_text()
    
    assert "HERSmokeStrategy" in content, "Should reference HERSmokeStrategy"
