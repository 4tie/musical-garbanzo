"""
Tests for Freqtrade strategy detection and validation service.
"""
from pathlib import Path
import pytest

from app.schemas.freqtrade_strategy import FreqtradeStrategyFile
from app.services.freqtrade_strategy_service import FreqtradeStrategyService


class DummyCommandRunner:
    def __init__(self, success=True, stdout="", stderr=""):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr

    def run(self, command, **kwargs):
        from app.schemas.freqtrade import FreqtradeCommandResult
        return FreqtradeCommandResult(
            command=command,
            success=self.success,
            stdout=self.stdout,
            stderr=self.stderr,
            return_code=0 if self.success else 1,
            duration=0.1,
            blocked=False,
            timed_out=False,
        )


def make_service(command_runner=None):
    return FreqtradeStrategyService(command_runner=command_runner)


def test_lists_py_files_in_strategies_dir(tmp_path, monkeypatch):
    """Test that .py files in strategies directory are listed."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy files
    (strategies_dir / "MyStrategy.py").write_text("# strategy code")
    (strategies_dir / "AnotherStrategy.py").write_text("# another strategy")
    (strategies_dir / "__init__.py").write_text("# init file")

    service = make_service()
    result = service.list_strategy_files()

    assert len(result.strategies) == 2
    strategy_names = [s.strategy_name for s in result.strategies]
    assert "MyStrategy" in strategy_names
    assert "AnotherStrategy" in strategy_names
    assert "__init__" not in strategy_names


def test_detects_sidecar_json(tmp_path, monkeypatch):
    """Test that sidecar .json files are detected."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy with sidecar
    (strategies_dir / "MyStrategy.py").write_text("# strategy code")
    (strategies_dir / "MyStrategy.json").write_text('{"params": {}}')

    service = make_service()
    result = service.list_strategy_files()

    assert len(result.strategies) == 1
    strategy = result.strategies[0]
    assert strategy.strategy_name == "MyStrategy"
    assert strategy.has_sidecar_json is True
    assert strategy.params_path is not None


def test_missing_sidecar_warning(tmp_path, monkeypatch):
    """Test that missing sidecar generates a warning."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy without sidecar
    (strategies_dir / "MyStrategy.py").write_text("# strategy code")

    service = make_service()
    result = service.list_strategy_files()

    assert len(result.strategies) == 1
    strategy = result.strategies[0]
    assert strategy.has_sidecar_json is False
    assert "sidecar" in strategy.warnings[0].lower()
    assert "sidecar" in result.warnings[0].lower()


def test_unsafe_path_rejected(tmp_path, monkeypatch):
    """Test that paths outside strategies directory are rejected."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    service = make_service()

    # Test path outside strategies dir
    is_valid, error = service.validate_strategy_file_path("/etc/passwd")
    assert is_valid is False
    assert "not within strategies directory" in error

    # Test non-.py file
    is_valid, error = service.validate_strategy_file_path(str(strategies_dir / "config.json"))
    assert is_valid is False
    assert "not a .py file" in error


def test_unsafe_strategy_name_rejected():
    """Test that unsafe strategy names are rejected."""
    service = make_service()

    # Empty name
    is_valid, error = service.validate_strategy_name("")
    assert is_valid is False
    assert "cannot be empty" in error

    # Path traversal
    is_valid, error = service.validate_strategy_name("../etc/passwd")
    assert is_valid is False
    assert "alphanumeric" in error.lower()

    # Invalid characters
    is_valid, error = service.validate_strategy_name("My Strategy!")
    assert is_valid is False
    assert "alphanumeric" in error.lower()


def test_freqtrade_missing_returns_controlled_status(tmp_path, monkeypatch):
    """Test that missing Freqtrade returns controlled status."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy file
    (strategies_dir / "MyStrategy.py").write_text("# strategy code")

    # Mock command runner that fails
    command_runner = DummyCommandRunner(success=False, stderr="Freqtrade not found")
    service = make_service(command_runner)

    result = service.list_strategies_via_freqtrade()

    assert result.freqtrade_visible is False
    assert len(result.strategies) == 0
    assert len(result.errors) > 0


def test_no_strategy_code_import_happens(tmp_path, monkeypatch):
    """Test that strategy code is not imported."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy with malicious code
    malicious_code = """
import sys
sys.exit(1)  # This should NOT execute
"""
    (strategies_dir / "MaliciousStrategy.py").write_text(malicious_code)

    service = make_service()
    result = service.list_strategy_files()

    # Should successfully list without executing code
    assert len(result.strategies) == 1
    assert result.strategies[0].strategy_name == "MaliciousStrategy"


def test_no_file_overwrite_happens(tmp_path, monkeypatch):
    """Test that strategy files are not overwritten."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy file
    original_content = "# original strategy code"
    (strategies_dir / "MyStrategy.py").write_text(original_content)

    service = make_service()
    service.list_strategy_files()
    service.find_strategy_by_name("MyStrategy")

    # File should not be modified
    assert (strategies_dir / "MyStrategy.py").read_text() == original_content


def test_find_strategy_by_name(tmp_path, monkeypatch):
    """Test finding a strategy by name."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy files
    (strategies_dir / "MyStrategy.py").write_text("# strategy code")
    (strategies_dir / "MyStrategy.json").write_text('{"params": {}}')
    (strategies_dir / "OtherStrategy.py").write_text("# other strategy")

    service = make_service()

    strategy = service.find_strategy_by_name("MyStrategy")
    assert strategy is not None
    assert strategy.strategy_name == "MyStrategy"
    assert strategy.has_sidecar_json is True

    strategy = service.find_strategy_by_name("OtherStrategy")
    assert strategy is not None
    assert strategy.has_sidecar_json is False

    strategy = service.find_strategy_by_name("NonExistent")
    assert strategy is None


def test_list_strategies_via_freqtrade(tmp_path, monkeypatch):
    """Test listing strategies via Freqtrade command."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy files
    (strategies_dir / "MyStrategy.py").write_text("# strategy code")
    (strategies_dir / "MyStrategy.json").write_text('{"params": {}}')

    # Mock command runner with Freqtrade output
    freqtrade_output = "MyStrategy: MyStrategyClass\nOtherStrategy: OtherStrategyClass"
    command_runner = DummyCommandRunner(success=True, stdout=freqtrade_output)
    service = make_service(command_runner)

    result = service.list_strategies_via_freqtrade()

    assert result.freqtrade_visible is True
    assert result.source == "freqtrade"
    assert len(result.strategies) == 2
    assert result.strategies[0].strategy_name == "MyStrategy"
    assert result.strategies[0].class_name == "MyStrategyClass"


def test_get_strategy_status(tmp_path, monkeypatch):
    """Test getting strategy status."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy file
    (strategies_dir / "MyStrategy.py").write_text("# strategy code")

    service = make_service()
    status = service.get_strategy_status("MyStrategy")

    assert status.strategy_name == "MyStrategy"
    assert status.exists is True
    assert status.freqtrade_visible is False  # Freqtrade not configured
    assert status.has_sidecar_json is False


def test_get_strategy_status_not_found(tmp_path, monkeypatch):
    """Test getting status for non-existent strategy."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    service = make_service()
    status = service.get_strategy_status("NonExistent")

    assert status.strategy_name == "NonExistent"
    assert status.exists is False
    assert status.freqtrade_visible is False
    assert len(status.errors) > 0


def test_get_strategy_status_invalid_name():
    """Test getting status for invalid strategy name."""
    service = make_service()
    status = service.get_strategy_status("Invalid Name!")

    assert status.strategy_name == "Invalid Name!"
    assert status.exists is False
    assert status.freqtrade_visible is False
    assert len(status.errors) > 0


def test_strategies_directory_not_exists(tmp_path, monkeypatch):
    """Test handling when strategies directory does not exist."""
    from app.core.config import settings

    # Don't create strategies directory
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    service = make_service()
    result = service.list_strategy_files()

    assert len(result.strategies) == 0
    assert len(result.errors) > 0
    assert "does not exist" in result.errors[0]


def test_detect_sidecar_json_method(tmp_path, monkeypatch):
    """Test the detect_sidecar_json method directly."""
    from app.core.config import settings

    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create strategy with sidecar
    py_path = strategies_dir / "MyStrategy.py"
    py_path.write_text("# strategy code")
    json_path = strategies_dir / "MyStrategy.json"
    json_path.write_text('{"params": {}}')

    service = make_service()
    sidecar = service.detect_sidecar_json(py_path)

    assert sidecar is not None
    assert sidecar == json_path

    # Test without sidecar
    py_path2 = strategies_dir / "NoSidecar.py"
    py_path2.write_text("# no sidecar")
    sidecar2 = service.detect_sidecar_json(py_path2)

    assert sidecar2 is None
