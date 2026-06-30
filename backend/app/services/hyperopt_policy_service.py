"""
Hyperopt policy service for Part 08 optimization pipeline.
Enforces safety rules for hyperopt execution.
"""
from typing import Any, Dict, List, Optional

from app.schemas.optimization import HyperoptPolicy, OptimizationRequest


class HyperoptPolicyService:
    """Service for managing hyperopt safety policies."""

    def __init__(self) -> None:
        """Initialize the hyperopt policy service."""
        self._default_policies = {
            "conservative": self._build_conservative_policy(),
            "balanced": self._build_balanced_policy(),
            "aggressive": self._build_aggressive_policy(),
        }

    def get_default_policy(
        self, risk_profile: str = "balanced", timeframe: Optional[str] = None
    ) -> HyperoptPolicy:
        """
        Get the default hyperopt policy for a given risk profile.

        Args:
            risk_profile: Risk profile (conservative, balanced, aggressive)
            timeframe: Optional timeframe for policy adjustments

        Returns:
            HyperoptPolicy with safe defaults
        """
        if risk_profile not in self._default_policies:
            risk_profile = "balanced"

        policy = self._default_policies[risk_profile].model_copy()

        # Adjust min_trades based on timeframe if provided
        if timeframe:
            policy.min_trades = self.get_min_trades(timeframe, risk_profile)

        return policy

    def validate_request_against_policy(
        self, request: OptimizationRequest, policy: HyperoptPolicy
    ) -> List[str]:
        """
        Validate an optimization request against the policy.

        Args:
            request: Optimization request to validate
            policy: Hyperopt policy to validate against

        Returns:
            List of validation warnings (empty if valid)
        """
        warnings: List[str] = []

        # Check epochs
        if request.epochs > policy.max_epochs:
            warnings.append(
                f"Requested epochs ({request.epochs}) exceeds policy max ({policy.max_epochs}). "
                f"Will be capped to {policy.max_epochs}."
            )

        # Check spaces
        invalid_spaces = []
        for space in request.spaces:
            if space not in policy.allowed_spaces:
                invalid_spaces.append(space)

        if invalid_spaces:
            warnings.append(
                f"Requested spaces {invalid_spaces} are not in policy allowed spaces. "
                f"Allowed: {policy.allowed_spaces}. Invalid spaces will be removed."
            )

        # Check locked spaces
        locked_attempted = []
        for space in request.spaces:
            if space in policy.locked_spaces:
                locked_attempted.append(space)

        if locked_attempted:
            warnings.append(
                f"Requested spaces {locked_attempted} are locked by policy. "
                f"Locked spaces will be removed."
            )

        # Check ROI optimization
        if "roi" in request.spaces and not policy.allow_roi_optimization:
            warnings.append(
                "ROI optimization is disabled by policy. 'roi' space will be removed."
            )

        # Check stoploss optimization
        if "stoploss" in request.spaces and not policy.allow_stoploss_optimization:
            warnings.append(
                "Stoploss optimization is disabled by policy. 'stoploss' space will be removed."
            )

        # Check trailing optimization
        if "trailing" in request.spaces and not policy.allow_trailing_optimization:
            warnings.append(
                "Trailing optimization is disabled by policy. 'trailing' space will be removed."
            )

        # Check user confirmation
        if not request.user_confirmed:
            warnings.append(
                "User confirmation is required before hyperopt execution. "
                "Set user_confirmed=True to proceed."
            )

        return warnings

    def normalize_spaces(self, spaces: List[str], policy: HyperoptPolicy) -> List[str]:
        """
        Normalize requested spaces according to policy.

        Args:
            spaces: Requested spaces
            policy: Hyperopt policy

        Returns:
            Normalized spaces list (only allowed, non-locked spaces)
        """
        normalized = []

        for space in spaces:
            # Skip locked spaces
            if space in policy.locked_spaces:
                continue

            # Skip spaces not allowed by policy
            if space not in policy.allowed_spaces:
                continue

            # Skip spaces where optimization is disabled
            if space == "roi" and not policy.allow_roi_optimization:
                continue
            if space == "stoploss" and not policy.allow_stoploss_optimization:
                continue
            if space == "trailing" and not policy.allow_trailing_optimization:
                continue

            normalized.append(space)

        # If no spaces remain, use default
        if not normalized:
            normalized = ["buy", "sell"]

        return normalized

    def get_min_trades(self, timeframe: str, risk_profile: str) -> int:
        """
        Get minimum trade count threshold based on timeframe and risk profile.

        Args:
            timeframe: Timeframe (e.g., 1m, 5m, 1h, 1d)
            risk_profile: Risk profile (conservative, balanced, aggressive)

        Returns:
            Minimum trade count threshold
        """
        # Base thresholds by risk profile
        base_thresholds = {
            "conservative": 50,
            "balanced": 30,
            "aggressive": 20,
        }

        base = base_thresholds.get(risk_profile, 30)

        # Adjust based on timeframe (shorter timeframes need more trades)
        timeframe_multipliers = {
            "1m": 2.0,
            "3m": 1.5,
            "5m": 1.2,
            "15m": 1.0,
            "30m": 0.9,
            "1h": 0.8,
            "2h": 0.7,
            "4h": 0.6,
            "6h": 0.5,
            "12h": 0.4,
            "1d": 0.3,
        }

        multiplier = timeframe_multipliers.get(timeframe.lower(), 1.0)
        min_trades = int(base * multiplier)

        # Ensure at least 10 trades
        return max(min_trades, 10)

    def build_policy_summary(self, policy: HyperoptPolicy) -> Dict[str, Any]:
        """
        Build a human-readable policy summary.

        Args:
            policy: Hyperopt policy

        Returns:
            Dictionary with policy summary
        """
        return {
            "max_epochs": policy.max_epochs,
            "default_epochs": policy.default_epochs,
            "allowed_spaces": policy.allowed_spaces,
            "locked_spaces": policy.locked_spaces,
            "max_optimized_parameters": policy.max_optimized_parameters,
            "roi_optimization_allowed": policy.allow_roi_optimization,
            "stoploss_optimization_allowed": policy.allow_stoploss_optimization,
            "trailing_optimization_allowed": policy.allow_trailing_optimization,
            "timeout_seconds": policy.timeout_seconds,
            "min_trades": policy.min_trades,
            "stop_on_zero_trades": policy.stop_on_zero_trades,
            "notes": policy.notes,
        }

    def _build_conservative_policy(self) -> HyperoptPolicy:
        """Build conservative hyperopt policy."""
        return HyperoptPolicy(
            max_epochs=100,
            default_epochs=25,
            allowed_spaces=["buy", "sell"],
            locked_spaces=["roi", "stoploss", "trailing", "protection"],
            max_optimized_parameters=4,
            allow_roi_optimization=False,
            allow_stoploss_optimization=False,
            allow_trailing_optimization=False,
            timeout_seconds=1800,  # 30 minutes
            min_trades=50,
            stop_on_zero_trades=True,
            notes="Conservative policy: lower epochs, higher trade threshold, shorter timeout",
        )

    def _build_balanced_policy(self) -> HyperoptPolicy:
        """Build balanced hyperopt policy."""
        return HyperoptPolicy(
            max_epochs=200,
            default_epochs=50,
            allowed_spaces=["buy", "sell"],
            locked_spaces=["roi", "stoploss", "trailing", "protection"],
            max_optimized_parameters=6,
            allow_roi_optimization=False,
            allow_stoploss_optimization=False,
            allow_trailing_optimization=False,
            timeout_seconds=3600,  # 1 hour
            min_trades=30,
            stop_on_zero_trades=True,
            notes="Balanced policy: moderate epochs, moderate trade threshold, standard timeout",
        )

    def _build_aggressive_policy(self) -> HyperoptPolicy:
        """Build aggressive hyperopt policy."""
        return HyperoptPolicy(
            max_epochs=300,
            default_epochs=100,
            allowed_spaces=["buy", "sell"],
            locked_spaces=["roi", "stoploss", "trailing", "protection"],
            max_optimized_parameters=8,
            allow_roi_optimization=False,
            allow_stoploss_optimization=False,
            allow_trailing_optimization=False,
            timeout_seconds=7200,  # 2 hours
            min_trades=20,
            stop_on_zero_trades=True,
            notes="Aggressive policy: higher epochs, lower trade threshold, longer timeout",
        )
