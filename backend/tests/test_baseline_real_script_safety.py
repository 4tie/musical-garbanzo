"""
Safety tests for the baseline evaluation CLI script.

These tests verify that the script follows safety rules without actually
executing the real script (which would run real Freqtrade backtests).
"""
import ast
import pytest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "run-baseline-evaluation.py"


class TestBaselineRealScriptSafety:
    """Safety tests for the baseline evaluation CLI script."""

    def test_script_exists(self):
        """Script file must exist."""
        assert SCRIPT_PATH.exists(), f"Script not found at {SCRIPT_PATH}"

    def test_script_imports_baseline_evaluation_service(self):
        """Script must import and use BaselineEvaluationService."""
        script_content = SCRIPT_PATH.read_text()
        assert "BaselineEvaluationService" in script_content
        assert "from app.services.baseline_evaluation_service" in script_content

    def test_script_requires_user_confirmed_for_real_execution(self):
        """Script must require --user-confirmed flag for real execution."""
        script_content = SCRIPT_PATH.read_text()
        assert "--user-confirmed" in script_content
        assert "user_confirmed" in script_content

    def test_script_does_not_call_ollama(self):
        """Script must not call Ollama (AST-based check)."""
        # This is covered by test_script_parse_tree_no_ollama_imports
        pass

    def test_script_does_not_call_discord(self):
        """Script must not call Discord (AST-based check)."""
        # This is covered by test_script_parse_tree_no_discord_imports
        pass

    def test_script_does_not_contain_approval_logic(self):
        """Script must not contain approval logic."""
        script_content = SCRIPT_PATH.read_text()
        # Check for actual approval logic, not just mentions in comments
        lines = script_content.split('\n')
        code_lines = [line for line in lines if not line.strip().startswith('#') and not line.strip().startswith('"""')]
        code_content = '\n'.join(code_lines)
        # Check for approval function calls or assignments
        assert "approve(" not in code_content.lower()
        assert ".approve" not in code_content.lower()
        assert "approved = " not in code_content.lower()

    def test_script_does_not_contain_export_logic(self):
        """Script must not contain export logic."""
        script_content = SCRIPT_PATH.read_text()
        # Check for actual export logic, not just mentions in comments
        lines = script_content.split('\n')
        code_lines = [line for line in lines if not line.strip().startswith('#') and not line.strip().startswith('"""')]
        code_content = '\n'.join(code_lines)
        # Check for export function calls or assignments
        assert "export(" not in code_content.lower()
        assert ".export" not in code_content.lower()
        assert "export_strategy" not in code_content.lower()

    def test_script_does_not_create_fake_metrics(self):
        """Script must not create fake metrics."""
        script_content = SCRIPT_PATH.read_text()
        # Check for actual fake data creation, not just mentions in comments
        lines = script_content.split('\n')
        code_lines = [line for line in lines if not line.strip().startswith('#') and not line.strip().startswith('"""')]
        code_content = '\n'.join(code_lines)
        # Check for fake/mock data assignments
        assert "fake = " not in code_content.lower()
        assert "mock = " not in code_content.lower()
        assert "dummy = " not in code_content.lower()

    def test_script_does_not_run_unsafe_freqtrade_commands(self):
        """Script must not directly run unsafe Freqtrade commands."""
        script_content = SCRIPT_PATH.read_text()
        # Check for actual subprocess calls, not just mentions in comments
        lines = script_content.split('\n')
        code_lines = [line for line in lines if not line.strip().startswith('#') and not line.strip().startswith('"""')]
        code_content = '\n'.join(code_lines)
        assert "subprocess" not in code_content.lower()
        assert "os.system" not in code_content.lower()

    def test_script_contains_expected_final_markers(self):
        """Script must contain expected final status markers."""
        script_content = SCRIPT_PATH.read_text()
        assert "REAL_BASELINE_EVALUATION_PASSED" in script_content
        assert "REAL_BASELINE_EVALUATION_FAILED_CONTROLLED" in script_content
        assert "REAL_BASELINE_EVALUATION_CONFIRMATION_REQUIRED" in script_content

    def test_script_uses_baseline_evaluation_request(self):
        """Script must use BaselineEvaluationRequest."""
        script_content = SCRIPT_PATH.read_text()
        assert "BaselineEvaluationRequest" in script_content
        assert "from app.schemas.baseline" in script_content

    def test_script_has_safety_rules_comment(self):
        """Script should have safety rules documented in comments."""
        script_content = SCRIPT_PATH.read_text()
        assert "safety" in script_content.lower() or "Safety" in script_content

    def test_script_no_live_trading_logic(self):
        """Script must not contain live trading logic."""
        script_content = SCRIPT_PATH.read_text()
        # Check for actual live trading logic, not just mentions in comments
        lines = script_content.split('\n')
        code_lines = [line for line in lines if not line.strip().startswith('#') and not line.strip().startswith('"""')]
        code_content = '\n'.join(code_lines)
        # Check for live trading function calls or assignments
        assert "live_trading" not in code_content.lower()
        assert "start_trading" not in code_content.lower()
        assert "dry_run" not in code_content.lower()

    def test_script_parse_tree_no_ollama_imports(self):
        """Parse script AST to ensure no Ollama imports."""
        script_content = SCRIPT_PATH.read_text()
        tree = ast.parse(script_content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "ollama" not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "ollama" not in node.module.lower()

    def test_script_parse_tree_no_discord_imports(self):
        """Parse script AST to ensure no Discord imports."""
        script_content = SCRIPT_PATH.read_text()
        tree = ast.parse(script_content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "discord" not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "discord" not in node.module.lower()

    def test_script_has_required_cli_arguments(self):
        """Script must have required CLI arguments."""
        script_content = SCRIPT_PATH.read_text()
        assert "--strategy" in script_content
        assert "--pair" in script_content
        assert "--timeframe" in script_content
        assert "--risk-profile" in script_content
        assert "--download-missing-data" in script_content
        assert "--user-confirmed" in script_content

    def test_script_prints_structured_output(self):
        """Script must print structured output with key fields."""
        script_content = SCRIPT_PATH.read_text()
        assert "run_id" in script_content
        assert "strategy_name" in script_content
        assert "status" in script_content
        assert "classification" in script_content
        assert "confidence_score" in script_content
        assert "trade_count" in script_content
        assert "profit_factor" in script_content
        assert "expectancy" in script_content
        assert "max_drawdown" in script_content
