"""
Tests for Freqtrade data availability and download service.
"""
from pathlib import Path
import pytest

from app.schemas.freqtrade_data import (
    FreqtradeDataCheckRequest,
    FreqtradeDataDownloadRequest,
)
from app.services.freqtrade_data_service import FreqtradeDataService


class DummyCommandRunner:
    def __init__(self, success=True, stdout="", stderr="", blocked=False):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.blocked = blocked

    def run(self, command, **kwargs):
        from app.schemas.freqtrade import FreqtradeCommandResult
        return FreqtradeCommandResult(
            command=command,
            success=self.success,
            stdout=self.stdout,
            stderr=self.stderr,
            return_code=0 if self.success else 1,
            duration_seconds=0.1,
            blocked=self.blocked,
            timed_out=False,
            error=self.stderr if not self.success else None,
        )


class FakeLogRepository:
    def __init__(self):
        self.entries = []

    def add_log(self, **kwargs):
        self.entries.append(kwargs)
        return kwargs


class FakeAuditRepository:
    def __init__(self):
        self.entries = []

    def create_audit_log(self, data):
        self.entries.append(data)
        return data


def make_service(command_runner=None):
    return FreqtradeDataService(
        command_runner=command_runner or DummyCommandRunner(),
        log_repository=FakeLogRepository(),
        audit_repository=FakeAuditRepository(),
    )


def test_build_list_data_command():
    """Test building list-data command."""
    service = make_service()
    request = FreqtradeDataCheckRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframe="1h",
    )

    command = service.build_list_data_command(request)

    assert "list-data" in command
    assert "--userdir" in command
    assert "--show-timerange" in command


def test_build_list_data_command_with_config():
    """Test building list-data command with config path."""
    service = make_service()
    request = FreqtradeDataCheckRequest(
        config_path="/path/to/config.json",
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframe="1h",
    )

    command = service.build_list_data_command(request)

    assert "list-data" in command
    assert "--config" in command
    assert "/path/to/config.json" in command


def test_build_download_data_command():
    """Test building download-data command."""
    service = make_service()
    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT", "ETH/USDT"],
        timeframes=["1h", "5m"],
        days=30,
        user_confirmed=True,
    )

    command = service.build_download_data_command(request)

    assert "download-data" in command
    assert "--pairs" in command
    assert "BTC/USDT,ETH/USDT" in command
    assert "--timeframes" in command
    assert "1h,5m" in command
    assert "--days" in command
    assert "30" in command
    assert "--trading-mode" in command
    assert "--data-format-ohlcv" in command


def test_build_download_data_command_with_timerange():
    """Test building download-data command with timerange."""
    service = make_service()
    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        timerange="20240101-20240131",
        user_confirmed=True,
    )

    command = service.build_download_data_command(request)

    assert "download-data" in command
    assert "--timerange" in command
    assert "20240101-20240131" in command


def test_erase_never_appears():
    """Test that --erase never appears in download command."""
    service = make_service()
    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        days=30,
        user_confirmed=True,
    )

    command = service.build_download_data_command(request)

    assert "--erase" not in command
    assert "erase" not in " ".join(command).lower()


def test_empty_pairs_rejected():
    """Test that empty pairs list is rejected."""
    with pytest.raises(ValueError, match="pairs must not be empty"):
        FreqtradeDataCheckRequest(
            exchange="binance",
            pairs=[],
            timeframe="1h",
        )


def test_empty_timeframes_rejected():
    """Test that empty timeframes list is rejected."""
    with pytest.raises(ValueError, match="timeframes must not be empty"):
        FreqtradeDataDownloadRequest(
            exchange="binance",
            pairs=["BTC/USDT"],
            timeframes=[],
            days=30,
            user_confirmed=True,
        )


def test_download_blocked_without_confirmation():
    """Test that download is blocked without user confirmation."""
    with pytest.raises(ValueError, match="user_confirmed must be true"):
        FreqtradeDataDownloadRequest(
            exchange="binance",
            pairs=["BTC/USDT"],
            timeframes=["1h"],
            days=30,
            user_confirmed=False,
        )


def test_download_blocked_without_days_or_timerange():
    """Test that download is blocked without days or timerange."""
    with pytest.raises(ValueError, match="Either days or timerange must be provided"):
        FreqtradeDataDownloadRequest(
            exchange="binance",
            pairs=["BTC/USDT"],
            timeframes=["1h"],
            user_confirmed=True,
        )


def test_missing_freqtrade_returns_controlled_status(tmp_path, monkeypatch):
    """Test that missing Freqtrade returns controlled status."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", None)
    monkeypatch.setattr(settings, "FREQTRADE_CONFIG_DIR", str(tmp_path / "config"))

    service = make_service()
    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        days=30,
        user_confirmed=True,
    )

    result = service.download_data(request)

    assert result.success is False
    assert result.blocked is True
    assert "Freqtrade is not configured" in result.error


def test_download_blocked_without_confirmation_at_runtime(tmp_path, monkeypatch):
    """Test that download is blocked at runtime even if request passes validation."""
    from app.core.config import settings

    # Create a dummy config file to make Freqtrade appear configured
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.json"
    config_file.write_text("{}")

    monkeypatch.setattr(settings, "FREQTRADE_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(settings, "FREQTRADE_DEFAULT_CONFIG", str(config_file))

    service = make_service()
    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        days=30,
        user_confirmed=True,
    )

    # Override user_confirmed after validation
    request.user_confirmed = False

    result = service.download_data(request)

    assert result.success is False
    assert result.blocked is True
    assert "User confirmation required" in result.error


def test_discover_local_data_files(tmp_path, monkeypatch):
    """Test discovering local data files."""
    from app.core.config import settings

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    # Create data file
    exchange_dir = data_dir / "binance" / "1h"
    exchange_dir.mkdir(parents=True)
    (exchange_dir / "BTC_USDT.json").write_text("{}")

    service = make_service()
    pair_statuses = service.discover_local_data_files("binance", "spot", ["BTC/USDT"], "1h")

    assert len(pair_statuses) == 1
    assert pair_statuses[0].pair == "BTC/USDT"
    assert pair_statuses[0].exists is True
    assert pair_statuses[0].file_path is not None


def test_discover_local_data_files_missing(tmp_path, monkeypatch):
    """Test discovering local data files when missing."""
    from app.core.config import settings

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    service = make_service()
    pair_statuses = service.discover_local_data_files("binance", "spot", ["BTC/USDT"], "1h")

    assert len(pair_statuses) == 1
    assert pair_statuses[0].pair == "BTC/USDT"
    assert pair_statuses[0].exists is False
    assert pair_statuses[0].file_path is None


def test_check_data_via_freqtrade(tmp_path, monkeypatch):
    """Test checking data via Freqtrade command."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    freqtrade_output = "BTC/USDT, 1h, 20240101-20240131\nETH/USDT, 1h, 20240101-20240131"
    command_runner = DummyCommandRunner(success=True, stdout=freqtrade_output)
    service = make_service(command_runner)

    request = FreqtradeDataCheckRequest(
        exchange="binance",
        pairs=["BTC/USDT", "ETH/USDT"],
        timeframe="1h",
    )

    result = service.check_data(request)

    assert result.freqtrade_visible is True
    assert result.source == "freqtrade"
    assert len(result.pairs) == 2


def test_check_data_freqtrade_fails(tmp_path, monkeypatch):
    """Test controlled status when Freqtrade command fails."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    command_runner = DummyCommandRunner(success=False, stderr="Freqtrade error")
    service = make_service(command_runner)

    request = FreqtradeDataCheckRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframe="1h",
    )

    result = service.check_data(request)

    assert result.freqtrade_visible is False
    assert result.source == "freqtrade"
    assert len(result.errors) > 0


def test_download_data_success(tmp_path, monkeypatch):
    """Test successful data download."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    freqtrade_output = "Downloaded data for BTC/USDT"
    command_runner = DummyCommandRunner(success=True, stdout=freqtrade_output)
    service = make_service(command_runner)

    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        days=30,
        user_confirmed=True,
    )

    result = service.download_data(request)

    assert result.success is True
    assert result.blocked is False
    assert result.stdout == freqtrade_output


def test_download_data_failure(tmp_path, monkeypatch):
    """Test failed data download."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    command_runner = DummyCommandRunner(success=False, stderr="Download failed")
    service = make_service(command_runner)

    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        days=30,
        user_confirmed=True,
    )

    result = service.download_data(request)

    assert result.success is False
    assert result.blocked is False
    assert result.error is not None


def test_invalid_trading_mode_rejected():
    """Test that invalid trading mode is rejected."""
    with pytest.raises(ValueError, match="trading_mode must be one of"):
        FreqtradeDataCheckRequest(
            exchange="binance",
            pairs=["BTC/USDT"],
            timeframe="1h",
            trading_mode="live",
        )

    with pytest.raises(ValueError, match="trading_mode must be one of"):
        FreqtradeDataDownloadRequest(
            exchange="binance",
            pairs=["BTC/USDT"],
            timeframes=["1h"],
            days=30,
            user_confirmed=True,
            trading_mode="live",
        )


def test_no_secrets_exposed():
    """Test that secrets are not exposed in commands."""
    service = make_service()
    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        days=30,
        user_confirmed=True,
    )

    command = service.build_download_data_command(request)
    command_str = " ".join(command)

    # Check for secret-like patterns
    secret_patterns = ["api_key", "secret", "password", "token", "key="]
    for pattern in secret_patterns:
        assert pattern not in command_str.lower()


def test_get_data_dir(tmp_path, monkeypatch):
    """Test getting data directory path."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path))

    service = make_service()
    data_dir = service.get_data_dir()

    assert data_dir == tmp_path / "data"
