"""
Safety tests for the real smoke decision validation script.

These tests statically inspect the script. They do not execute real validation.
"""
from pathlib import Path
import re


SCRIPT_PATH = (
    Path(__file__).parent.parent.parent
    / "scripts"
    / "evaluate-real-smoke-decision.py"
)


def extract_code_only(content: str) -> str:
    """Extract executable code, excluding comments and docstrings."""
    lines = content.splitlines()
    code_lines = []
    in_docstring = False
    delimiter = None

    for line in lines:
        stripped = line.strip()
        if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
            delimiter = stripped[:3]
            if stripped.count(delimiter) < 2:
                in_docstring = True
            continue
        if in_docstring:
            if delimiter and delimiter in stripped:
                in_docstring = False
                delimiter = None
            continue
        if stripped.startswith("#"):
            continue
        code_lines.append(line)
    return "\n".join(code_lines)


def test_script_exists():
    """Real decision validation script exists."""
    assert SCRIPT_PATH.exists()


def test_script_references_decision_service():
    """Script uses DecisionService for evaluation."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "DecisionService" in content
    assert "evaluate_run" in content


def test_script_does_not_contain_external_execution():
    """Script does not execute external commands."""
    code_only = extract_code_only(SCRIPT_PATH.read_text(encoding="utf-8"))
    forbidden_patterns = [
        r"subprocess\.",
        r"os\.system",
        r"exec\(",
        r"popen",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), pattern


def test_script_does_not_contain_freqtrade_execution():
    """Script does not reference real tool execution APIs."""
    code_only = extract_code_only(SCRIPT_PATH.read_text(encoding="utf-8"))
    forbidden_patterns = [
        r"services\.freqtrade",
        r"Freqtrade[A-Za-z]+Service",
        r"CommandRunner",
        r"BacktestRunner",
        r"DataService",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), pattern


def test_script_does_not_contain_download_data():
    """Script does not contain download-data command text."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "download-data" not in content
    assert "download_data" not in content


def test_script_does_not_contain_backtesting():
    """Script does not contain backtesting command text."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "backtesting" not in content


def test_script_does_not_call_ollama():
    """Script does not import or call Ollama."""
    code_only = extract_code_only(SCRIPT_PATH.read_text(encoding="utf-8"))
    forbidden_patterns = [
        r"import.*ollama",
        r"from.*ollama",
        r"ollama\.",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), pattern


def test_script_does_not_call_discord():
    """Script does not import or call Discord."""
    code_only = extract_code_only(SCRIPT_PATH.read_text(encoding="utf-8"))
    forbidden_patterns = [
        r"import.*discord",
        r"from.*discord",
        r"discord\.",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, code_only, re.IGNORECASE), pattern


def test_script_does_not_contain_approved_export_action_logic():
    """Script does not contain approval or export action logic."""
    content = SCRIPT_PATH.read_text(encoding="utf-8").lower()
    forbidden_terms = [
        "approved",
        "approve",
        "exported",
        "export ",
        "export_",
        "live_ready",
        "live-ready",
    ]
    for term in forbidden_terms:
        assert term not in content, term


def test_script_expects_rejected_for_real_smoke_validation():
    """Script expects rejected as the passing real smoke classification."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    assert 'response.classification == "rejected"' in content
    assert "REAL_DECISION_PASSED" in content
    assert "REAL_DECISION_FAILED_UNEXPECTED_CLASSIFICATION" in content
