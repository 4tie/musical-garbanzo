"""
Tests for Part 12 strategy readiness gate service.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.strategies import (
    StrategyDetail,
    StrategyIssue,
    StrategyParamsSummary,
    StrategyReadiness,
)
from app.services.strategy_readiness_gate import (
    assert_strategy_ready_for_run,
    check_strategy_readiness,
)
from app.services.strategy_workspace_service import StrategyWorkspaceService
from app.services.strategy_workspace_utils import StrategyWorkspaceError


VALID_STRATEGY_SOURCE = """
from freqtrade.strategy import IStrategy


class TestStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    minimal_roi = {"0": 0.1}
    stoploss = -0.1
    buy_params = {"buy_rsi": 30}
    sell_params = {"sell_rsi": 70}

    def populate_indicators(self, dataframe, metadata):
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        return dataframe
"""


@pytest.fixture
def strategy_workspace(monkeypatch):
    """Create a temporary strategy workspace for testing."""
    project_root = Path(settings.project_root).resolve()
    user_data_dir = project_root / ".pytest_runtime" / "strategy-readiness-gate" / "user_data"
    strategies_dir = user_data_dir / "strategies"
    shutil.rmtree(user_data_dir.parent, ignore_errors=True)
    strategies_dir.mkdir(parents=True)

    monkeypatch.setattr(
        settings,
        "FREQTRADE_USER_DATA_DIR",
        str(user_data_dir.relative_to(project_root)),
    )

    yield strategies_dir

    shutil.rmtree(user_data_dir.parent, ignore_errors=True)


def write_strategy(strategies_dir: Path, name: str = "TestStrategy", source: str | None = None) -> None:
    """Write a strategy file to the workspace."""
    strategy_source = (source or VALID_STRATEGY_SOURCE).replace("TestStrategy", name)
    (strategies_dir / f"{name}.py").write_text(strategy_source, encoding="utf-8")


def write_sidecar(strategies_dir: Path, name: str = "TestStrategy", payload: dict | None = None) -> None:
    """Write a sidecar JSON file to the workspace."""
    (strategies_dir / f"{name}.json").write_text(
        json.dumps(
            payload
            or {
                "buy": {"buy_rsi": 30},
                "sell": {"sell_rsi": 70},
                "roi": {"0": 0.1},
                "stoploss": -0.1,
                "timeframe": "5m",
            }
        ),
        encoding="utf-8",
    )


class TestStrategyReadinessGate:
    """Tests for strategy readiness gate service."""

    def test_ready_allowed(self, strategy_workspace):
        """Test that ready strategies are allowed for execution."""
        write_strategy(strategy_workspace, "ReadyStrategy")
        write_sidecar(strategy_workspace, "ReadyStrategy")

        result = assert_strategy_ready_for_run("ReadyStrategy", "baseline")

        assert result.strategy_name == "ReadyStrategy"
        assert result.readiness == StrategyReadiness.READY
        assert result.allowed is True
        assert len(result.issues) == 0
        assert "ready for baseline execution" in result.message.lower()

    def test_warning_allowed(self, strategy_workspace):
        """Test that warning strategies are allowed for execution."""
        write_strategy(strategy_workspace, "WarningStrategy")
        write_sidecar(strategy_workspace, "WarningStrategy")

        result = assert_strategy_ready_for_run("WarningStrategy", "optimization")

        assert result.strategy_name == "WarningStrategy"
        assert result.readiness in (StrategyReadiness.READY, StrategyReadiness.WARNING)
        assert result.allowed is True
        assert "ready for optimization execution" in result.message.lower()

    def test_missing_sidecar_blocked(self, strategy_workspace):
        """Test that missing_sidecar strategies are blocked."""
        write_strategy(strategy_workspace, "MissingSidecarStrategy")
        # No sidecar written

        with pytest.raises(HTTPException) as exc_info:
            assert_strategy_ready_for_run("MissingSidecarStrategy", "baseline")

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["error"] is True
        assert detail["code"] == "strategy_not_ready"
        assert detail["strategy_name"] == "MissingSidecarStrategy"
        assert detail["readiness"] == "missing_sidecar"
        assert "missing required sidecar" in detail["message"].lower()

    def test_invalid_blocked(self, strategy_workspace):
        """Test that invalid strategies are blocked."""
        # Write invalid strategy (missing required methods)
        invalid_source = """
from freqtrade.strategy import IStrategy

class InvalidStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    # Missing required methods and fields
"""
        write_strategy(strategy_workspace, "InvalidStrategy", invalid_source)
        write_sidecar(strategy_workspace, "InvalidStrategy")  # Add sidecar so it's not missing_sidecar

        with pytest.raises(HTTPException) as exc_info:
            assert_strategy_ready_for_run("InvalidStrategy", "baseline")

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["error"] is True
        assert detail["readiness"] in ("invalid", "parse_error")

    def test_parse_error_blocked(self, strategy_workspace):
        """Test that parse_error strategies are blocked."""
        # Write strategy with syntax error
        parse_error_source = """
from freqtrade.strategy import IStrategy

class ParseErrorStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    minimal_roi = {"0": 0.1
    # Missing closing brace - syntax error
"""
        write_strategy(strategy_workspace, "ParseErrorStrategy", parse_error_source)

        with pytest.raises(HTTPException) as exc_info:
            assert_strategy_ready_for_run("ParseErrorStrategy", "baseline")

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["error"] is True
        assert detail["readiness"] == "parse_error"
        assert "parsing errors" in detail["message"].lower()

    def test_unsafe_blocked(self, strategy_workspace):
        """Test that unsafe strategies are blocked."""
        write_strategy(strategy_workspace, "UnsafeStrategy")
        write_sidecar(strategy_workspace, "UnsafeStrategy")

        # Mock service to return unsafe readiness
        mock_service = MagicMock(spec=StrategyWorkspaceService)
        mock_detail = StrategyDetail(
            strategy_name="UnsafeStrategy",
            strategy_file_path="strategies/UnsafeStrategy.py",
            sidecar_json_path="strategies/UnsafeStrategy.json",
            has_sidecar=True,
            readiness=StrategyReadiness.UNSAFE,
            issues=[
                StrategyIssue(
                    code="unsafe_pattern",
                    severity="critical",
                    message="Contains unsafe pattern",
                )
            ],
            warnings=[],
            metadata={},
            params_summary=StrategyParamsSummary(strategy_name="UnsafeStrategy"),
            class_name="UnsafeStrategy",
            file_name="UnsafeStrategy.py",
            apparent_strategy_name="UnsafeStrategy",
            syntax_valid=True,
            static_checks={},
        )
        mock_service.get_strategy.return_value = mock_detail

        with pytest.raises(HTTPException) as exc_info:
            assert_strategy_ready_for_run("UnsafeStrategy", "baseline", mock_service)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["error"] is True
        assert detail["readiness"] == "unsafe"
        assert "unsafe patterns" in detail["message"].lower()

    def test_missing_strategy_blocked(self, strategy_workspace):
        """Test that missing strategies are blocked."""
        # Don't write any strategy

        with pytest.raises(HTTPException) as exc_info:
            assert_strategy_ready_for_run("NonExistentStrategy", "baseline")

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["error"] is True
        assert detail["readiness"] == StrategyReadiness.UNSAFE

    def test_unsafe_strategy_name_blocked(self, strategy_workspace):
        """Test that unsafe strategy names are blocked."""
        # Try to use a path traversal name
        with pytest.raises(HTTPException) as exc_info:
            assert_strategy_ready_for_run("../etc/passwd", "baseline")

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["error"] is True
        assert detail["readiness"] == StrategyReadiness.UNSAFE

    def test_strategy_file_not_executed(self, strategy_workspace):
        """Test that strategy files are not executed during readiness check."""
        write_strategy(strategy_workspace, "NoExecutionStrategy")
        write_sidecar(strategy_workspace, "NoExecutionStrategy")

        # The check should complete without executing the strategy code
        # If it tried to execute, it would fail due to missing dependencies
        result = assert_strategy_ready_for_run("NoExecutionStrategy", "baseline")

        assert result.allowed is True
        assert result.readiness == StrategyReadiness.READY

    def test_check_strategy_readiness_non_asserting(self, strategy_workspace):
        """Test that check_strategy_readiness returns result without raising."""
        write_strategy(strategy_workspace, "CheckStrategy")
        write_sidecar(strategy_workspace, "CheckStrategy")

        result = check_strategy_readiness("CheckStrategy")

        assert result.strategy_name == "CheckStrategy"
        assert result.allowed is True
        assert result.readiness == StrategyReadiness.READY

    def test_check_strategy_readiness_missing_sidecar(self, strategy_workspace):
        """Test check_strategy_readiness with missing sidecar."""
        write_strategy(strategy_workspace, "MissingSidecarCheck")
        # No sidecar

        result = check_strategy_readiness("MissingSidecarCheck")

        assert result.strategy_name == "MissingSidecarCheck"
        assert result.allowed is False
        assert result.readiness == StrategyReadiness.MISSING_SIDECAR
        assert len(result.next_actions) > 0

    def test_check_strategy_readiness_load_error(self, strategy_workspace):
        """Test check_strategy_readiness handles load errors gracefully."""
        # Mock service to raise error
        mock_service = MagicMock(spec=StrategyWorkspaceService)
        mock_service.get_strategy.side_effect = StrategyWorkspaceError("Load failed")

        result = check_strategy_readiness("LoadErrorStrategy", mock_service)

        assert result.strategy_name == "LoadErrorStrategy"
        assert result.allowed is False
        assert result.readiness == StrategyReadiness.UNSAFE
        assert len(result.issues) > 0
        assert any(issue.code == "strategy_load_error" for issue in result.issues)
        assert "Load failed" in result.issues[0].message

    def test_blocked_response_has_next_actions(self, strategy_workspace):
        """Test that blocked responses include next actions."""
        write_strategy(strategy_workspace, "BlockedStrategy")
        # No sidecar to trigger blocked state

        with pytest.raises(HTTPException) as exc_info:
            assert_strategy_ready_for_run("BlockedStrategy", "baseline")

        detail = exc_info.value.detail
        assert "next_actions" in detail
        assert len(detail["next_actions"]) > 0
        assert any("workspace" in action.lower() for action in detail["next_actions"])

    def test_run_type_in_message(self, strategy_workspace):
        """Test that run type is included in success message."""
        write_strategy(strategy_workspace, "RunTypeStrategy")
        write_sidecar(strategy_workspace, "RunTypeStrategy")

        result_baseline = assert_strategy_ready_for_run("RunTypeStrategy", "baseline")
        assert "baseline" in result_baseline.message.lower()

        result_optimization = assert_strategy_ready_for_run("RunTypeStrategy", "optimization")
        assert "optimization" in result_optimization.message.lower()

    def test_custom_workspace_service(self, strategy_workspace):
        """Test that custom workspace service can be injected."""
        write_strategy(strategy_workspace, "CustomServiceStrategy")
        write_sidecar(strategy_workspace, "CustomServiceStrategy")

        mock_service = StrategyWorkspaceService()
        result = assert_strategy_ready_for_run("CustomServiceStrategy", "baseline", mock_service)

        assert result.allowed is True
        assert result.strategy_name == "CustomServiceStrategy"
