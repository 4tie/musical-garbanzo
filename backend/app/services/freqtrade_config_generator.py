"""
Safe Freqtrade backtest configuration generator.
"""
import json
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.repositories.artifacts import ArtifactRepository
from app.schemas.artifacts import ArtifactCreate
from app.schemas.freqtrade_config import (
    FreqtradeBacktestConfigRequest,
    FreqtradeBacktestConfigResult,
)


SECRET_KEY_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "private_key",
    "app_secret",
    "discord_token",
    "exchange_key",
    "key",
)

DISABLED_API_SERVER_JWT_PLACEHOLDER = "her-disabled-api-server-placeholder-00000000"


class FreqtradeConfigGenerator:
    """Generate safe Freqtrade backtest configurations."""

    def __init__(
        self,
        artifact_repository: Optional[ArtifactRepository] = None,
    ) -> None:
        self.artifact_repository = artifact_repository or ArtifactRepository()

    def build_backtest_config(self, request: FreqtradeBacktestConfigRequest) -> dict:
        """
        Build a Freqtrade backtest configuration dictionary.

        Args:
            request: Backtest config request

        Returns:
            Freqtrade configuration dictionary
        """
        config = {
            "max_open_trades": request.max_open_trades,
            "stake_currency": request.stake_currency,
            "stake_amount": request.stake_amount,
            "dry_run": True,
            "dry_run_wallet": request.dry_run_wallet,
            "cancel_open_orders_on_exit": request.cancel_open_orders_on_exit,
            "trading_mode": request.trading_mode,
            "timeframe": request.timeframe,
            "unfilledtimeout": {
                "entry": 10,
                "exit": 10,
                "exit_timeout_count": 0,
                "unit": "minutes",
            },
            "entry_pricing": {
                "price_side": "same",
                "use_order_book": True,
                "order_book_top": 1,
                "price_last_balance": 0.0,
                "check_depth_of_market": {
                    "enabled": False,
                    "bids_to_ask_delta": 1,
                },
            },
            "exit_pricing": {
                "price_side": "same",
                "use_order_book": True,
                "order_book_top": 1,
            },
            "exchange": {
                "name": request.exchange,
                "key": "",
                "secret": "",
                "ccxt_config": {},
                "ccxt_async_config": {},
                "pair_whitelist": request.pairs,
                "pair_blacklist": [],
            },
            "pairlists": [
                {
                    "method": "StaticPairList",
                }
            ],
            "dataformat_ohlcv": request.data_format_ohlcv,
            "user_data_dir": str(settings.freqtrade_user_data_dir_path),
            "strategy": request.strategy_name,
            "telegram": {
                "enabled": False,
                "token": "",
                "chat_id": "",
            },
            "api_server": {
                "enabled": False,
                "listen_ip_address": "127.0.0.1",
                "listen_port": 8080,
                "verbosity": "error",
                "enable_openapi": False,
                "jwt_secret_key": DISABLED_API_SERVER_JWT_PLACEHOLDER,
                "CORS_origins": [],
                "username": "",
                "password": "",
            },
            "bot_name": "her_backtest",
            "initial_state": "running",
            "force_entry_enable": False,
            "internals": {
                "process_throttle_secs": 5,
            },
        }

        if request.timerange:
            config["timerange"] = request.timerange

        if request.additional_safe_config:
            config.update(request.additional_safe_config)

        self.validate_config_has_no_secrets(config)

        return config

    def write_backtest_config(self, request: FreqtradeBacktestConfigRequest) -> FreqtradeBacktestConfigResult:
        """
        Build and write a Freqtrade backtest configuration to disk.

        Args:
            request: Backtest config request

        Returns:
            Backtest config result with path and artifact info
        """
        try:
            config = self.build_backtest_config(request)
            config_path = self.get_run_config_path(request.run_id)

            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            artifact_id = self._register_config_artifact(request.run_id, config_path)

            return FreqtradeBacktestConfigResult(
                run_id=request.run_id,
                config_path=str(config_path),
                config=self.sanitize_config_for_response(config),
                artifact_id=artifact_id,
                success=True,
            )
        except Exception as exc:
            return FreqtradeBacktestConfigResult(
                run_id=request.run_id,
                config_path="",
                config={},
                success=False,
                error=str(exc),
            )

    def get_run_config_path(self, run_id: str) -> Path:
        """
        Get the configuration file path for a specific run.

        Args:
            run_id: Run UUID

        Returns:
            Path to the run's backtest config file
        """
        config_dir = settings.freqtrade_config_dir_path / "runs"
        return config_dir / f"{run_id}.backtest.json"

    @staticmethod
    def validate_config_has_no_secrets(config: dict) -> None:
        """
        Validate that a configuration does not contain secret-like values.

        Args:
            config: Configuration dictionary

        Raises:
            ValueError: If secret-like keys are found with non-empty values
        """
        def check_dict(d: dict, path: str = "") -> None:
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                key_lower = key.lower()

                if FreqtradeConfigGenerator._is_secret_like_key(key_lower):
                    if value == DISABLED_API_SERVER_JWT_PLACEHOLDER:
                        continue
                    if value and value != "":
                        raise ValueError(f"Config contains secret-like key with value: {current_path}")

                if isinstance(value, dict):
                    check_dict(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            check_dict(item, f"{current_path}[{i}]")

        check_dict(config)

    @staticmethod
    def sanitize_config_for_response(config: dict) -> dict:
        """
        Sanitize configuration for API response by redacting any secret-like values.

        Args:
            config: Configuration dictionary

        Returns:
            Sanitized configuration dictionary
        """
        def sanitize(d: dict) -> dict:
            sanitized = {}
            for key, value in d.items():
                key_lower = key.lower()
                if FreqtradeConfigGenerator._is_secret_like_key(key_lower) and value:
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, dict):
                    sanitized[key] = sanitize(value)
                elif isinstance(value, list):
                    sanitized[key] = [
                        sanitize(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    sanitized[key] = value
            return sanitized

        return sanitize(config)

    @staticmethod
    def _is_secret_like_key(key_lower: str) -> bool:
        """Return whether a config key should be treated as secret-bearing."""
        return (
            key_lower in SECRET_KEY_MARKERS
            or key_lower.endswith("_key")
            or key_lower.endswith("-key")
            or "secret" in key_lower
            or "token" in key_lower
            or "password" in key_lower
        )

    def _register_config_artifact(self, run_id: str, config_path: Path) -> Optional[str]:
        """
        Register the generated config as an artifact.

        Args:
            run_id: Run UUID
            config_path: Path to the generated config file

        Returns:
            Artifact ID
        """
        try:
            artifact = self.artifact_repository.create_artifact(
                ArtifactCreate(
                    run_id=run_id,
                    artifact_type="freqtrade_config",
                    file_path=str(config_path),
                    description="Freqtrade backtest configuration",
                )
            )
            return artifact["id"]
        except Exception:
            return None
