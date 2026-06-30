"""
Tests for Freqtrade backtest config generator.
"""
import json
from pathlib import Path
import pytest

from app.schemas.freqtrade_config import FreqtradeBacktestConfigRequest
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator


class FakeArtifactRepository:
    def __init__(self):
        self.artifacts = []

    def create_artifact(self, data):
        artifact = {"id": "artifact-123", **data.dict()}
        self.artifacts.append(artifact)
        return artifact


def make_generator():
    return FreqtradeConfigGenerator(artifact_repository=FakeArtifactRepository())


def test_valid_config_generated(tmp_path, monkeypatch):
    """Test that a valid config is generated correctly."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path / "user_data"))

    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT", "ETH/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    config = generator.build_backtest_config(request)

    assert config["max_open_trades"] == 3
    assert config["stake_currency"] == "USDT"
    assert config["stake_amount"] == "unlimited"
    assert config["dry_run"] is True
    assert config["dry_run_wallet"] == 10000.0
    assert config["cancel_open_orders_on_exit"] is True
    assert config["trading_mode"] == "spot"
    assert config["timeframe"] == "1h"
    assert config["exchange"]["name"] == "binance"
    assert config["exchange"]["key"] == ""
    assert config["exchange"]["secret"] == ""
    assert config["exchange"]["pair_whitelist"] == ["BTC/USDT", "ETH/USDT"]
    assert config["strategy"] == "MyStrategy"
    assert config["dataformat_ohlcv"] == "feather"


def test_file_written_to_expected_path(tmp_path, monkeypatch):
    """Test that config file is written to the expected path."""
    from app.core.config import settings

    config_dir = tmp_path / "config"
    monkeypatch.setattr(settings, "FREQTRADE_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path / "user_data"))

    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    result = generator.write_backtest_config(request)

    expected_path = config_dir / "runs" / "run-123.backtest.json"
    assert result.config_path == str(expected_path)
    assert expected_path.exists()

    with open(expected_path) as f:
        loaded_config = json.load(f)
    assert loaded_config["strategy"] == "MyStrategy"


def test_pairs_included():
    """Test that pairs are included in the config."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    config = generator.build_backtest_config(request)

    assert config["exchange"]["pair_whitelist"] == ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


def test_strategy_included():
    """Test that strategy name is included in the config."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="TestStrategy",
    )

    config = generator.build_backtest_config(request)

    assert config["strategy"] == "TestStrategy"


def test_dry_run_is_true():
    """Test that dry_run is always set to True."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    config = generator.build_backtest_config(request)

    assert config["dry_run"] is True


def test_exchange_key_secret_are_empty():
    """Test that exchange key and secret are always empty."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    config = generator.build_backtest_config(request)

    assert config["exchange"]["key"] == ""
    assert config["exchange"]["secret"] == ""


def test_no_secret_like_values_present():
    """Test that no secret-like values are present in the config."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    config = generator.build_backtest_config(request)

    generator.validate_config_has_no_secrets(config)


def test_disabled_api_server_jwt_placeholder_is_schema_valid_and_redacted():
    """Freqtrade requires a JWT value even when HER disables the API server."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    config = generator.build_backtest_config(request)
    jwt_placeholder = config["api_server"]["jwt_secret_key"]

    assert config["api_server"]["enabled"] is False
    assert len(jwt_placeholder) >= 32
    generator.validate_config_has_no_secrets(config)

    sanitized = generator.sanitize_config_for_response(config)
    assert sanitized["api_server"]["jwt_secret_key"] == "[REDACTED]"


def test_artifact_registered(tmp_path, monkeypatch):
    """Test that the config is registered as an artifact."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setattr(settings, "FREQTRADE_USER_DATA_DIR", str(tmp_path / "user_data"))

    fake_repo = FakeArtifactRepository()
    generator = FreqtradeConfigGenerator(artifact_repository=fake_repo)
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
    )

    result = generator.write_backtest_config(request)

    assert result.artifact_id == "artifact-123"
    assert len(fake_repo.artifacts) == 1
    assert fake_repo.artifacts[0]["artifact_type"] == "freqtrade_config"
    assert fake_repo.artifacts[0]["run_id"] == "run-123"


def test_invalid_empty_pairs_rejected():
    """Test that empty pairs list is rejected."""
    generator = make_generator()

    with pytest.raises(ValueError, match="pairs must not be empty"):
        FreqtradeBacktestConfigRequest(
            run_id="run-123",
            pairs=[],
            timeframe="1h",
            strategy_name="MyStrategy",
        )


def test_unsafe_strategy_name_rejected():
    """Test that unsafe strategy names are rejected."""
    generator = make_generator()

    with pytest.raises(ValueError, match="strategy_name must be safe"):
        FreqtradeBacktestConfigRequest(
            run_id="run-123",
            pairs=["BTC/USDT"],
            timeframe="1h",
            strategy_name="My Strategy!",  # Contains space and special char
        )

    with pytest.raises(ValueError, match="strategy_name must be safe"):
        FreqtradeBacktestConfigRequest(
            run_id="run-123",
            pairs=["BTC/USDT"],
            timeframe="1h",
            strategy_name="",  # Empty
        )


def test_invalid_trading_mode_rejected():
    """Test that invalid trading mode is rejected."""
    generator = make_generator()

    with pytest.raises(ValueError, match="trading_mode must be one of"):
        FreqtradeBacktestConfigRequest(
            run_id="run-123",
            pairs=["BTC/USDT"],
            timeframe="1h",
            strategy_name="MyStrategy",
            trading_mode="live",  # Invalid
        )


def test_secrets_in_additional_config_rejected():
    """Test that secret-like keys in additional config are rejected."""
    generator = make_generator()

    with pytest.raises(ValueError, match="additional_safe_config must not contain secret-like keys"):
        FreqtradeBacktestConfigRequest(
            run_id="run-123",
            pairs=["BTC/USDT"],
            timeframe="1h",
            strategy_name="MyStrategy",
            additional_safe_config={"api_key": "secret123"},
        )


def test_timerange_included_when_provided():
    """Test that timerange is included when provided."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
        timerange="20240101-20240131",
    )

    config = generator.build_backtest_config(request)

    assert config["timerange"] == "20240101-20240131"


def test_additional_safe_config_merged():
    """Test that additional safe config is merged into the generated config."""
    generator = make_generator()
    request = FreqtradeBacktestConfigRequest(
        run_id="run-123",
        pairs=["BTC/USDT"],
        timeframe="1h",
        strategy_name="MyStrategy",
        additional_safe_config={"position_stacking": True, "use_exit_signal": False},
    )

    config = generator.build_backtest_config(request)

    assert config["position_stacking"] is True
    assert config["use_exit_signal"] is False


def test_sanitize_config_for_response():
    """Test that config is sanitized for response."""
    generator = make_generator()
    config_with_secrets = {
        "exchange": {
            "name": "binance",
            "key": "secret-key",
            "secret": "secret-value",
        },
        "api_key": "another-secret",
    }

    sanitized = generator.sanitize_config_for_response(config_with_secrets)

    assert sanitized["exchange"]["key"] == "[REDACTED]"
    assert sanitized["exchange"]["secret"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["exchange"]["name"] == "binance"


def test_validate_config_with_secrets_raises_error():
    """Test that validation raises error when secrets are present."""
    generator = make_generator()
    config_with_secrets = {
        "exchange": {
            "name": "binance",
            "key": "secret-key",
        },
    }

    with pytest.raises(ValueError, match="Config contains secret-like key"):
        generator.validate_config_has_no_secrets(config_with_secrets)


def test_empty_timeframe_rejected():
    """Test that empty timeframe is rejected."""
    generator = make_generator()

    with pytest.raises(ValueError, match="timeframe must not be empty"):
        FreqtradeBacktestConfigRequest(
            run_id="run-123",
            pairs=["BTC/USDT"],
            timeframe="",
            strategy_name="MyStrategy",
        )

    with pytest.raises(ValueError, match="timeframe must not be empty"):
        FreqtradeBacktestConfigRequest(
            run_id="run-123",
            pairs=["BTC/USDT"],
            timeframe="   ",
            strategy_name="MyStrategy",
        )
