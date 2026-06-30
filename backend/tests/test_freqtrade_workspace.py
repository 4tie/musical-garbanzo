"""
Tests for Freqtrade workspace path resolution and validation.
"""
from pathlib import Path

import pytest

from app.services.freqtrade_workspace import FreqtradeWorkspaceService


class DummySettings:
    def __init__(self, root: Path) -> None:
        self._project_root = root
        self.FREQTRADE_USER_DATA_DIR = "./freqtrade_workspace/user_data"
        self.FREQTRADE_CONFIG_DIR = "./freqtrade_workspace/config"
        self.FREQTRADE_DEFAULT_CONFIG = "./freqtrade_workspace/config/config.generated.json"

    @property
    def project_root(self) -> Path:
        return self._project_root


def test_workspace_paths_resolve_correctly(tmp_path):
    settings = DummySettings(tmp_path)
    service = FreqtradeWorkspaceService(settings)

    paths = service.get_paths()

    assert paths["user_data_dir"] == tmp_path / "freqtrade_workspace" / "user_data"
    assert paths["strategy_dir"] == tmp_path / "freqtrade_workspace" / "user_data" / "strategies"
    assert paths["data_dir"] == tmp_path / "freqtrade_workspace" / "user_data" / "data"
    assert paths["backtest_results_dir"] == tmp_path / "freqtrade_workspace" / "user_data" / "backtest_results"
    assert paths["hyperopt_results_dir"] == tmp_path / "freqtrade_workspace" / "user_data" / "hyperopt_results"
    assert paths["config_dir"] == tmp_path / "freqtrade_workspace" / "config"
    assert paths["default_config"] == tmp_path / "freqtrade_workspace" / "config" / "config.generated.json"


def test_missing_workspace_dirs_can_be_created(tmp_path):
    settings = DummySettings(tmp_path)
    service = FreqtradeWorkspaceService(settings)

    initial = service.validate_workspace()
    assert initial.valid is False
    assert "user_data" in initial.missing_dirs
    assert "config" in initial.missing_dirs

    created = service.ensure_workspace()

    assert created.valid is True
    assert set(created.created_dirs) == {
        "user_data",
        "config",
        "strategies",
        "data",
        "backtest_results",
        "hyperopt_results",
        "hyperopts",
        "plot",
        "logs",
    }
    assert service.get_strategy_dir().is_dir()
    assert service.get_data_dir().is_dir()
    assert service.get_backtest_results_dir().is_dir()
    assert service.get_hyperopt_results_dir().is_dir()
    assert service.get_config_dir().is_dir()


def test_validate_workspace_returns_structured_status(tmp_path):
    settings = DummySettings(tmp_path)
    service = FreqtradeWorkspaceService(settings)
    service.ensure_workspace()

    status = service.validate_workspace()

    assert status.valid is True
    assert status.missing_dirs == []
    assert status.user_data_dir == str(service.get_user_data_dir())
    assert status.config_dir == str(service.get_config_dir())
    assert {directory.key for directory in status.directories} == {
        "user_data",
        "config",
        "strategies",
        "data",
        "backtest_results",
        "hyperopt_results",
        "hyperopts",
        "plot",
        "logs",
    }
    assert all(directory.exists for directory in status.directories)
    assert all(directory.is_dir for directory in status.directories)


def test_ensure_workspace_does_not_overwrite_existing_strategy_files(tmp_path):
    settings = DummySettings(tmp_path)
    service = FreqtradeWorkspaceService(settings)
    service.ensure_workspace()

    strategy_file = service.get_strategy_dir() / "ExistingStrategy.py"
    strategy_file.write_text("class ExistingStrategy: pass\n")

    status = service.ensure_workspace()

    assert status.valid is True
    assert strategy_file.read_text() == "class ExistingStrategy: pass\n"


def test_run_artifact_paths_reject_unsafe_run_id(tmp_path):
    settings = DummySettings(tmp_path)
    service = FreqtradeWorkspaceService(settings)

    assert service.get_run_config_dir("run-123") == tmp_path / "artifacts" / "runs" / "run-123" / "configs"
    assert service.get_run_raw_freqtrade_dir("run-123") == tmp_path / "artifacts" / "runs" / "run-123" / "freqtrade_raw"
    assert service.get_run_log_dir("run-123") == tmp_path / "artifacts" / "runs" / "run-123" / "logs"

    with pytest.raises(ValueError):
        service.get_run_config_dir("../bad")
