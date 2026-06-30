"""
Tests for Part 08 hyperopt policy service.
"""
import pytest

from app.schemas.optimization import HyperoptPolicy, OptimizationRequest
from app.services.hyperopt_policy_service import HyperoptPolicyService


@pytest.fixture
def policy_service():
    """Create a HyperoptPolicyService instance."""
    return HyperoptPolicyService()


@pytest.fixture
def sample_request():
    """Sample optimization request."""
    return OptimizationRequest(
        strategy_name="TestStrategy",
        pairs=["BTC/USDT", "ETH/USDT"],
        timeframe="5m",
        exchange="binance",
        epochs=50,
        spaces=["buy", "sell"],
        risk_profile="balanced",
        user_confirmed=True,
    )


class TestHyperoptPolicyService:
    """Test HyperoptPolicyService methods."""

    def test_get_default_policy_balanced(self, policy_service):
        """Test getting default balanced policy."""
        policy = policy_service.get_default_policy("balanced")

        assert policy.max_epochs == 200
        assert policy.default_epochs == 50
        assert policy.allowed_spaces == ["buy", "sell"]
        assert policy.locked_spaces == ["roi", "stoploss", "trailing", "protection"]
        assert policy.max_optimized_parameters == 6
        assert policy.allow_roi_optimization is False
        assert policy.allow_stoploss_optimization is False
        assert policy.allow_trailing_optimization is False
        assert policy.timeout_seconds == 3600
        assert policy.min_trades == 30
        assert policy.stop_on_zero_trades is True

    def test_get_default_policy_conservative(self, policy_service):
        """Test getting default conservative policy."""
        policy = policy_service.get_default_policy("conservative")

        assert policy.max_epochs == 100
        assert policy.default_epochs == 25
        assert policy.min_trades == 50
        assert policy.timeout_seconds == 1800

    def test_get_default_policy_aggressive(self, policy_service):
        """Test getting default aggressive policy."""
        policy = policy_service.get_default_policy("aggressive")

        assert policy.max_epochs == 300
        assert policy.default_epochs == 100
        assert policy.min_trades == 20
        assert policy.timeout_seconds == 7200

    def test_get_default_policy_invalid_profile(self, policy_service):
        """Test that invalid risk profile defaults to balanced."""
        policy = policy_service.get_default_policy("invalid")

        assert policy.max_epochs == 200  # Balanced default
        assert policy.default_epochs == 50

    def test_validate_request_against_policy_valid(self, policy_service, sample_request):
        """Test validation of valid request."""
        policy = policy_service.get_default_policy("balanced")
        warnings = policy_service.validate_request_against_policy(sample_request, policy)

        assert len(warnings) == 0

    def test_validate_request_epochs_exceeds_max(self, policy_service):
        """Test validation when epochs exceed policy max."""
        # Schema validation prevents epochs > 200, so we test with a policy that has lower max
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            epochs=150,  # Within schema limit, but exceeds conservative policy max of 100
            user_confirmed=True,
        )
        policy = policy_service.get_default_policy("conservative")  # max_epochs=100
        warnings = policy_service.validate_request_against_policy(request, policy)

        assert len(warnings) == 1
        assert "exceeds policy max" in warnings[0]

    def test_validate_request_invalid_spaces(self, policy_service):
        """Test validation with spaces not in policy allowed list."""
        # Schema allows roi, but policy doesn't
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            spaces=["buy", "roi"],  # ROI is valid in schema but not in policy
            user_confirmed=True,
        )
        policy = policy_service.get_default_policy("balanced")
        warnings = policy_service.validate_request_against_policy(request, policy)

        # Should get warning about spaces not in policy allowed list
        assert len(warnings) >= 1
        assert any("not in policy allowed spaces" in w for w in warnings)

    def test_validate_request_locked_spaces(self, policy_service):
        """Test validation with locked spaces."""
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            spaces=["buy", "roi"],  # ROI is locked by default
            user_confirmed=True,
        )
        policy = policy_service.get_default_policy("balanced")
        warnings = policy_service.validate_request_against_policy(request, policy)

        # Should get at least one warning about locked spaces
        assert len(warnings) >= 1
        assert any("locked by policy" in w for w in warnings)

    def test_validate_request_user_confirmed_false(self, policy_service):
        """Test validation when user_confirmed is false."""
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            user_confirmed=False,
        )
        policy = policy_service.get_default_policy("balanced")
        warnings = policy_service.validate_request_against_policy(request, policy)

        assert len(warnings) == 1
        assert "User confirmation is required" in warnings[0]

    def test_normalize_spaces_allowed(self, policy_service):
        """Test normalizing allowed spaces."""
        policy = policy_service.get_default_policy("balanced")
        spaces = ["buy", "sell"]
        normalized = policy_service.normalize_spaces(spaces, policy)

        assert normalized == ["buy", "sell"]

    def test_normalize_spaces_removes_locked(self, policy_service):
        """Test that normalize_spaces removes locked spaces."""
        policy = policy_service.get_default_policy("balanced")
        spaces = ["buy", "sell", "roi", "stoploss"]
        normalized = policy_service.normalize_spaces(spaces, policy)

        assert normalized == ["buy", "sell"]
        assert "roi" not in normalized
        assert "stoploss" not in normalized

    def test_normalize_spaces_defaults_on_empty(self, policy_service):
        """Test that normalize_spaces defaults to buy,sell when empty."""
        policy = policy_service.get_default_policy("balanced")
        spaces = []
        normalized = policy_service.normalize_spaces(spaces, policy)

        assert normalized == ["buy", "sell"]

    def test_get_min_trades_balanced_5m(self, policy_service):
        """Test min trades for balanced 5m timeframe."""
        min_trades = policy_service.get_min_trades("5m", "balanced")

        assert min_trades == 36  # 30 * 1.2

    def test_get_min_trades_conservative_1m(self, policy_service):
        """Test min trades for conservative 1m timeframe."""
        min_trades = policy_service.get_min_trades("1m", "conservative")

        assert min_trades == 100  # 50 * 2.0

    def test_get_min_trades_aggressive_1d(self, policy_service):
        """Test min trades for aggressive 1d timeframe."""
        min_trades = policy_service.get_min_trades("1d", "aggressive")

        assert min_trades == 10  # max(20 * 0.3, 10)

    def test_get_min_trades_unknown_timeframe(self, policy_service):
        """Test min trades with unknown timeframe defaults to 1.0 multiplier."""
        min_trades = policy_service.get_min_trades("unknown", "balanced")

        assert min_trades == 30  # 30 * 1.0

    def test_build_policy_summary(self, policy_service):
        """Test building policy summary."""
        policy = policy_service.get_default_policy("balanced")
        summary = policy_service.build_policy_summary(policy)

        assert summary["max_epochs"] == 200
        assert summary["default_epochs"] == 50
        assert summary["allowed_spaces"] == ["buy", "sell"]
        assert summary["locked_spaces"] == ["roi", "stoploss", "trailing", "protection"]
        assert summary["roi_optimization_allowed"] is False
        assert summary["stoploss_optimization_allowed"] is False
        assert summary["trailing_optimization_allowed"] is False
        assert summary["timeout_seconds"] == 3600
        assert summary["min_trades"] == 30
        assert summary["stop_on_zero_trades"] is True

    def test_get_default_policy_with_timeframe(self, policy_service):
        """Test getting policy with timeframe adjustment."""
        policy = policy_service.get_default_policy("balanced", timeframe="1m")

        # Min trades should be adjusted for 1m timeframe
        assert policy.min_trades == 60  # 30 * 2.0
