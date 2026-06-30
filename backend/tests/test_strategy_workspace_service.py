"""
Tests for Part 11 strategy workspace service.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.core.config import settings
from app.schemas.strategies import StrategyReadiness
from app.services.strategy_workspace_service import StrategyWorkspaceService


VALID_STRATEGY_SOURCE = """
from freqtrade.strategy import IStrategy


class TestStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 0.1}
    stoploss = -0.1
    trailing_stop = False
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
    project_root = Path(settings.project_root).resolve()
    user_data_dir = project_root / ".pytest_runtime" / "strategy-workspace-service" / "user_data"
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


@pytest.fixture
def service(strategy_workspace):
    return StrategyWorkspaceService()


def write_strategy(strategies_dir: Path, name: str = "TestStrategy", source: str | None = None) -> Path:
    strategy_source = (source or VALID_STRATEGY_SOURCE).replace("TestStrategy", name)
    path = strategies_dir / f"{name}.py"
    path.write_text(strategy_source, encoding="utf-8")
    return path


def write_sidecar(strategies_dir: Path, name: str = "TestStrategy", payload: dict | None = None) -> Path:
    path = strategies_dir / f"{name}.json"
    path.write_text(
        json.dumps(
            payload
            or {
                "buy": {"buy_rsi": 30},
                "sell": {"sell_rsi": 70},
                "roi": {"0": 0.1},
                "stoploss": -0.1,
                "trailing": {"trailing_stop": False},
                "timeframe": "5m",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_empty_workspace_returns_empty_list(service):
    assert service.list_strategies() == []


def test_valid_strategy_with_sidecar_is_ready(service, strategy_workspace):
    write_strategy(strategy_workspace)
    write_sidecar(strategy_workspace)

    strategies = service.list_strategies()
    detail = service.get_strategy("TestStrategy")

    assert len(strategies) == 1
    assert strategies[0].strategy_name == "TestStrategy"
    assert strategies[0].readiness == StrategyReadiness.READY
    assert detail.readiness == StrategyReadiness.READY
    assert detail.params_summary.parse_success is True


def test_valid_strategy_without_sidecar_is_missing_sidecar(service, strategy_workspace):
    write_strategy(strategy_workspace)

    detail = service.get_strategy("TestStrategy")

    assert detail.readiness == StrategyReadiness.MISSING_SIDECAR
    assert any(issue.code == "sidecar_missing" for issue in detail.issues)


def test_malformed_sidecar_is_parse_error(service, strategy_workspace):
    write_strategy(strategy_workspace)
    (strategy_workspace / "TestStrategy.json").write_text("{broken", encoding="utf-8")

    detail = service.get_strategy("TestStrategy")

    assert detail.readiness == StrategyReadiness.PARSE_ERROR
    assert any(issue.code == "sidecar_parse_error" for issue in detail.issues)


def test_invalid_python_syntax_is_parse_error(service, strategy_workspace):
    write_strategy(
        strategy_workspace,
        source="class TestStrategy(IStrategy):\n    def broken(:\n        pass\n",
    )
    write_sidecar(strategy_workspace)

    detail = service.get_strategy("TestStrategy")

    assert detail.readiness == StrategyReadiness.PARSE_ERROR
    assert any(issue.code == "python_syntax_error" for issue in detail.issues)


def test_unsafe_path_returns_unsafe_detail(service):
    detail = service.get_strategy("../TestStrategy")

    assert detail.readiness == StrategyReadiness.UNSAFE
    assert any(issue.code == "unsafe_path" for issue in detail.issues)


def test_private_cache_and_runtime_files_are_ignored(service, strategy_workspace):
    write_strategy(strategy_workspace, "VisibleStrategy")
    write_sidecar(strategy_workspace, "VisibleStrategy")
    write_strategy(strategy_workspace, "_PrivateStrategy")
    write_strategy(strategy_workspace, "VisibleStrategy_baseline_backup")
    (strategy_workspace / "__init__.py").write_text("", encoding="utf-8")

    strategies = service.list_strategies()

    assert [strategy.strategy_name for strategy in strategies] == ["VisibleStrategy"]


def test_suspicious_import_adds_warning_readiness(service, strategy_workspace):
    source = VALID_STRATEGY_SOURCE.replace(
        "from freqtrade.strategy import IStrategy",
        "from freqtrade.strategy import IStrategy\nimport requests",
    )
    write_strategy(strategy_workspace, source=source)
    write_sidecar(strategy_workspace)

    detail = service.get_strategy("TestStrategy")

    assert detail.readiness == StrategyReadiness.WARNING
    assert any(issue.code == "suspicious_import" for issue in detail.issues)


def test_dangerous_process_call_is_unsafe(service, strategy_workspace):
    source = VALID_STRATEGY_SOURCE.replace(
        "return dataframe",
        "import os\n        os.system('echo unsafe')\n        return dataframe",
        1,
    )
    write_strategy(strategy_workspace, source=source)
    write_sidecar(strategy_workspace)

    detail = service.get_strategy("TestStrategy")

    assert detail.readiness == StrategyReadiness.UNSAFE
    assert any(issue.code == "dangerous_process_call" for issue in detail.issues)


def test_file_write_pattern_is_unsafe(service, strategy_workspace):
    source = VALID_STRATEGY_SOURCE.replace(
        "from freqtrade.strategy import IStrategy",
        "from freqtrade.strategy import IStrategy\nfrom pathlib import Path",
    ).replace(
        "return dataframe",
        "Path('unsafe.txt').write_text('unsafe', encoding='utf-8')\n        return dataframe",
        1,
    )
    write_strategy(strategy_workspace, source=source)
    write_sidecar(strategy_workspace)

    detail = service.get_strategy("TestStrategy")

    assert detail.readiness == StrategyReadiness.UNSAFE
    assert any(issue.code == "file_write_pattern" for issue in detail.issues)


def test_incomplete_params_are_warning(service, strategy_workspace):
    write_strategy(strategy_workspace)
    write_sidecar(strategy_workspace, payload={"buy": {"buy_rsi": 30}})

    detail = service.validate_strategy("TestStrategy")

    assert detail.readiness == StrategyReadiness.WARNING
    assert any(issue.code == "params_sections_incomplete" for issue in detail.issues)


def test_get_strategy_params_returns_summary(service, strategy_workspace):
    write_strategy(strategy_workspace)
    write_sidecar(strategy_workspace)

    summary = service.get_strategy_params("TestStrategy")

    assert summary.strategy_name == "TestStrategy"
    assert summary.parse_success is True
    assert summary.timeframe == "5m"


def test_resolve_strategy_for_run_returns_static_detail(service, strategy_workspace):
    write_strategy(strategy_workspace)
    write_sidecar(strategy_workspace)

    detail = service.resolve_strategy_for_run("TestStrategy")

    assert detail.strategy_name == "TestStrategy"
    assert detail.readiness == StrategyReadiness.READY
