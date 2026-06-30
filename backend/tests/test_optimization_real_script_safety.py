"""
Safety tests for Part 08 optimization CLI script and Hyperopt smoke strategy.

These tests validate that:
- The CLI script exists and is safe
- The script does not call Ollama
- The script does not call Discord
- The script does not approve/export strategies
- The script requires user confirmation
- The script contains expected markers
- HERHyperoptSmokeStrategy exists and has hyperoptable parameters
- No live trading commands are used

IMPORTANT: These tests do NOT run real Hyperopt from pytest.
"""
import pytest
from pathlib import Path
import ast


class TestOptimizationRealScriptSafety:
    """Safety tests for optimization CLI script and Hyperopt smoke strategy."""

    def test_cli_script_exists(self):
        """Test that the CLI script exists."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        assert script_path.exists(), "CLI script scripts/run-optimization.py does not exist"
        assert script_path.is_file(), "CLI script is not a file"

    def test_cli_script_imports_pipeline_service(self):
        """Test that the CLI script imports OptimizationPipelineService."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        assert "OptimizationPipelineService" in script_content, \
            "CLI script does not import OptimizationPipelineService"
        assert "from app.services.optimization_pipeline_service import OptimizationPipelineService" in script_content, \
            "CLI script does not import OptimizationPipelineService correctly"

    def test_cli_script_requires_user_confirmation(self):
        """Test that the CLI script requires user confirmation."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        assert "--user-confirmed" in script_content, \
            "CLI script does not have --user-confirmed argument"
        assert "user_confirmed" in script_content, \
            "CLI script does not use user_confirmed parameter"

    def test_cli_script_does_not_call_ollama(self):
        """Test that the CLI script does not call Ollama."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        # Check for actual Ollama service calls, not just the word in documentation
        assert "import ollama" not in script_content.lower(), \
            "CLI script imports ollama"
        assert "from ollama" not in script_content.lower(), \
            "CLI script imports from ollama"
        assert "ollama." not in script_content.lower(), \
            "CLI script calls ollama methods"

    def test_cli_script_does_not_call_discord(self):
        """Test that the CLI script does not call Discord."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        # Check for actual Discord service calls, not just the word in documentation
        assert "import discord" not in script_content.lower(), \
            "CLI script imports discord"
        assert "from discord" not in script_content.lower(), \
            "CLI script imports from discord"
        assert "discord." not in script_content.lower(), \
            "CLI script calls discord methods"

    def test_cli_script_does_not_approve_export(self):
        """Test that the CLI script does not approve/export strategies."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_content = script_path.read_text()
        
        # Check for actual approve/export function calls, not just the word in documentation
        assert "approve_strategy" not in script_content.lower(), \
            "CLI script calls approve_strategy"
        assert "export_strategy" not in script_content.lower(), \
            "CLI script calls export_strategy"

    def test_cli_script_does_not_create_fake_metrics(self):
        """Test that the CLI script does not create fake metrics."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        assert "fake" not in script_content.lower(), \
            "CLI script contains 'fake' reference"
        assert "mock" not in script_content.lower(), \
            "CLI script contains 'mock' reference"
        assert "stub" not in script_content.lower(), \
            "CLI script contains 'stub' reference"

    def test_cli_script_contains_expected_markers(self):
        """Test that the CLI script contains expected final markers."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        assert "REAL_OPTIMIZATION_PIPELINE_PASSED" in script_content, \
            "CLI script does not contain REAL_OPTIMIZATION_PIPELINE_PASSED marker"
        assert "REAL_OPTIMIZATION_PIPELINE_FAILED_CONTROLLED" in script_content, \
            "CLI script does not contain REAL_OPTIMIZATION_PIPELINE_FAILED_CONTROLLED marker"
        assert "REAL_OPTIMIZATION_PIPELINE_CONFIRMATION_REQUIRED" in script_content, \
            "CLI script does not contain REAL_OPTIMIZATION_PIPELINE_CONFIRMATION_REQUIRED marker"

    def test_hyperopt_smoke_strategy_exists(self):
        """Test that HERHyperoptSmokeStrategy exists."""
        strategy_path = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERHyperoptSmokeStrategy.py"
        assert strategy_path.exists(), "HERHyperoptSmokeStrategy.py does not exist"
        assert strategy_path.is_file(), "HERHyperoptSmokeStrategy.py is not a file"

    def test_hyperopt_smoke_strategy_has_hyperoptable_parameters(self):
        """Test that HERHyperoptSmokeStrategy has hyperoptable parameters."""
        strategy_path = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERHyperoptSmokeStrategy.py"
        strategy_content = strategy_path.read_text()
        
        assert "IntParameter" in strategy_content, \
            "HERHyperoptSmokeStrategy does not have IntParameter"
        assert "DecimalParameter" in strategy_content or "IntParameter" in strategy_content, \
            "HERHyperoptSmokeStrategy does not have hyperoptable parameters"
        assert "space='buy'" in strategy_content, \
            "HERHyperoptSmokeStrategy does not have buy space parameters"
        assert "space='sell'" in strategy_content, \
            "HERHyperoptSmokeStrategy does not have sell space parameters"

    def test_hyperopt_smoke_strategy_no_live_trading(self):
        """Test that HERHyperoptSmokeStrategy has no live trading behavior."""
        strategy_path = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERHyperoptSmokeStrategy.py"
        strategy_content = strategy_path.read_text()
        
        assert "dry_run = True" in strategy_content, \
            "HERHyperoptSmokeStrategy does not have dry_run=True"
        # Check for actual live trading configuration, not just documentation
        assert "dry_run = False" not in strategy_content, \
            "HERHyperoptSmokeStrategy has dry_run=False"

    def test_hyperopt_smoke_strategy_no_secrets(self):
        """Test that HERHyperoptSmokeStrategy has no secrets."""
        strategy_path = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERHyperoptSmokeStrategy.py"
        strategy_content = strategy_path.read_text()
        
        # Check for actual secret usage in code, not just documentation
        lines = strategy_content.split('\n')
        code_lines = [line for line in lines if not line.strip().startswith('#') and not line.strip().startswith('"""')]
        code_content = '\n'.join(code_lines)
        
        assert "api_key" not in code_content.lower(), \
            "HERHyperoptSmokeStrategy contains api_key usage in code"
        assert "password" not in code_content.lower(), \
            "HERHyperoptSmokeStrategy contains password usage in code"

    def test_hyperopt_smoke_strategy_documented_as_test(self):
        """Test that HERHyperoptSmokeStrategy is documented as test/validation strategy."""
        strategy_path = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERHyperoptSmokeStrategy.py"
        strategy_content = strategy_path.read_text()
        
        assert "SMOKE TEST" in strategy_content, \
            "HERHyperoptSmokeStrategy is not documented as SMOKE TEST"
        assert "NOT a profitable strategy" in strategy_content, \
            "HERHyperoptSmokeStrategy is not documented as not profitable"
        assert "validation" in strategy_content.lower(), \
            "HERHyperoptSmokeStrategy is not documented as validation strategy"

    def test_cli_script_has_safety_documentation(self):
        """Test that the CLI script has safety documentation."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        assert "does NOT call Ollama" in script_content, \
            "CLI script does not document that it does not call Ollama"
        assert "does NOT send Discord" in script_content, \
            "CLI script does not document that it does not send Discord"
        assert "does NOT approve/export" in script_content, \
            "CLI script does not document that it does not approve/export"
        assert "does NOT guarantee profitability" in script_content, \
            "CLI script does not document that it does not guarantee profitability"

    def test_cli_script_parses_correctly(self):
        """Test that the CLI script parses as valid Python."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-optimization.py"
        script_content = script_path.read_text()
        
        try:
            ast.parse(script_content)
        except SyntaxError as e:
            pytest.fail(f"CLI script has syntax error: {e}")

    def test_hyperopt_smoke_strategy_parses_correctly(self):
        """Test that HERHyperoptSmokeStrategy parses as valid Python."""
        strategy_path = Path(__file__).parent.parent.parent / "freqtrade_workspace" / "user_data" / "strategies" / "HERHyperoptSmokeStrategy.py"
        strategy_content = strategy_path.read_text()
        
        try:
            ast.parse(strategy_content)
        except SyntaxError as e:
            pytest.fail(f"HERHyperoptSmokeStrategy has syntax error: {e}")
