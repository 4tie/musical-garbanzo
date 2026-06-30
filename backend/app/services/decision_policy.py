"""
Centralized Part 06 acceptance policies and thresholds.

This service defines threshold data only. It does not classify strategies,
persist decisions, run Freqtrade, call AI services, or send notifications.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.constants import DECISION_CLASSIFICATIONS, DECISION_POLICY_NAMES
from app.schemas.decisions import (
    DecisionPolicy,
    DecisionPolicySummary,
    MetricThresholds,
)


@dataclass(frozen=True)
class _RiskProfileDefaults:
    candidate_profit_factor: float
    promising_profit_factor: float
    validated_profit_factor: float
    max_drawdown_candidate: float
    max_drawdown_promising: float
    max_drawdown_validated: float
    min_expectancy_candidate: float
    min_expectancy_promising: float
    min_expectancy_validated: float
    high_drawdown_block_threshold: float


class DecisionPolicyService:
    """Build deterministic threshold policies for future decision gates."""

    RISK_PROFILE_ALIASES = {
        "moderate": "balanced",
    }

    POLICY_TO_RISK_PROFILE = {
        "default_conservative": "conservative",
        "default_balanced": "balanced",
        "default_aggressive": "aggressive",
    }

    RISK_PROFILE_DEFAULTS = {
        "conservative": _RiskProfileDefaults(
            candidate_profit_factor=1.15,
            promising_profit_factor=1.30,
            validated_profit_factor=1.50,
            max_drawdown_candidate=25.0,
            max_drawdown_promising=20.0,
            max_drawdown_validated=15.0,
            min_expectancy_candidate=0.00,
            min_expectancy_promising=0.05,
            min_expectancy_validated=0.10,
            high_drawdown_block_threshold=40.0,
        ),
        "balanced": _RiskProfileDefaults(
            candidate_profit_factor=1.10,
            promising_profit_factor=1.25,
            validated_profit_factor=1.40,
            max_drawdown_candidate=30.0,
            max_drawdown_promising=25.0,
            max_drawdown_validated=20.0,
            min_expectancy_candidate=0.00,
            min_expectancy_promising=0.03,
            min_expectancy_validated=0.08,
            high_drawdown_block_threshold=45.0,
        ),
        "aggressive": _RiskProfileDefaults(
            candidate_profit_factor=1.05,
            promising_profit_factor=1.18,
            validated_profit_factor=1.30,
            max_drawdown_candidate=40.0,
            max_drawdown_promising=35.0,
            max_drawdown_validated=30.0,
            min_expectancy_candidate=0.00,
            min_expectancy_promising=0.01,
            min_expectancy_validated=0.05,
            high_drawdown_block_threshold=55.0,
        ),
    }

    BASE_MIN_TRADES_BY_TIMEFRAME = {
        "1m": 500,
        "3m": 400,
        "5m": 300,
        "15m": 150,
        "30m": 100,
        "1h": 60,
        "2h": 40,
        "4h": 30,
        "1d": 20,
    }

    RISK_PROFILE_TRADE_MODIFIERS = {
        "conservative": 1.25,
        "balanced": 1.0,
        "aggressive": 0.8,
    }

    DEFAULT_TIMEFRAME = "1h"

    def get_policy(
        self,
        policy_name: Optional[str] = None,
        risk_profile: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> DecisionPolicy:
        """Return a policy for the requested policy name, risk profile, and timeframe."""
        normalized_policy_name = policy_name
        normalized_risk_profile = self._normalize_risk_profile(risk_profile)

        if normalized_policy_name:
            if normalized_policy_name not in DECISION_POLICY_NAMES:
                raise ValueError(
                    f"Unknown decision policy: {normalized_policy_name}. "
                    f"Allowed values: {', '.join(DECISION_POLICY_NAMES)}"
                )
            policy_risk_profile = self.POLICY_TO_RISK_PROFILE[normalized_policy_name]
            if normalized_risk_profile and normalized_risk_profile != policy_risk_profile:
                raise ValueError(
                    "policy_name and risk_profile refer to different risk profiles"
                )
            normalized_risk_profile = policy_risk_profile
        else:
            normalized_risk_profile = normalized_risk_profile or "balanced"
            normalized_policy_name = f"default_{normalized_risk_profile}"

        thresholds = self.get_thresholds(normalized_risk_profile, timeframe)
        return DecisionPolicy(
            policy_name=normalized_policy_name,
            risk_profile=normalized_risk_profile,
            timeframe=self._normalize_timeframe(timeframe),
            thresholds=thresholds,
            description=(
                f"{normalized_risk_profile.title()} baseline acceptance thresholds "
                "for already-parsed backtest evidence."
            ),
            notes=[
                "Thresholds are acceptance gates for parsed evidence only.",
                "They do not predict future returns.",
                "Future OOS, WFO, and robustness parts may tune or extend this policy.",
            ],
        )

    def get_default_policy(
        self,
        risk_profile: str = "balanced",
        timeframe: Optional[str] = None,
    ) -> DecisionPolicy:
        """Return the default policy for a risk profile."""
        return self.get_policy(risk_profile=risk_profile, timeframe=timeframe)

    def get_min_trades_for_timeframe(
        self,
        timeframe: Optional[str],
        risk_profile: str = "balanced",
    ) -> int:
        """Return the timeframe-aware minimum trade count after risk adjustment."""
        normalized_risk_profile = self._require_risk_profile(risk_profile)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        base_min_trades = self.BASE_MIN_TRADES_BY_TIMEFRAME[normalized_timeframe]
        modifier = self.RISK_PROFILE_TRADE_MODIFIERS[normalized_risk_profile]
        return int(round(base_min_trades * modifier))

    def get_thresholds(
        self,
        risk_profile: str,
        timeframe: Optional[str] = None,
    ) -> MetricThresholds:
        """Return metric thresholds for a risk profile and timeframe."""
        normalized_risk_profile = self._require_risk_profile(risk_profile)
        defaults = self.RISK_PROFILE_DEFAULTS[normalized_risk_profile]
        return MetricThresholds(
            min_trades=self.get_min_trades_for_timeframe(
                timeframe,
                normalized_risk_profile,
            ),
            candidate_profit_factor=defaults.candidate_profit_factor,
            promising_profit_factor=defaults.promising_profit_factor,
            validated_profit_factor=defaults.validated_profit_factor,
            max_drawdown_candidate=defaults.max_drawdown_candidate,
            max_drawdown_promising=defaults.max_drawdown_promising,
            max_drawdown_validated=defaults.max_drawdown_validated,
            min_expectancy_candidate=defaults.min_expectancy_candidate,
            min_expectancy_promising=defaults.min_expectancy_promising,
            min_expectancy_validated=defaults.min_expectancy_validated,
            min_win_rate_optional=None,
            single_pair_dependency_warning_threshold=0.80,
            high_drawdown_block_threshold=defaults.high_drawdown_block_threshold,
            min_pair_count_warning=2,
        )

    def summarize_policy(self, policy: DecisionPolicy) -> DecisionPolicySummary:
        """Return a compact, frontend-safe policy summary."""
        return DecisionPolicySummary(
            policy_name=policy.policy_name,
            display_name=f"{policy.risk_profile.title()} Decision Policy",
            description=policy.description,
            allowed_classifications=DECISION_CLASSIFICATIONS,
            gate_names=[
                "evidence_available",
                "decision_usable",
                "core_metrics_present",
                "trade_count_minimum",
                "profit_factor_minimum",
                "drawdown_maximum",
                "expectancy_minimum",
                "quality_flags_check",
                "single_pair_dependency_warning",
            ],
            risk_profile=policy.risk_profile,
            timeframe=policy.timeframe,
            thresholds=policy.thresholds,
            notes=policy.notes,
        )

    def _normalize_risk_profile(self, risk_profile: Optional[str]) -> Optional[str]:
        """Normalize risk-profile aliases while allowing None."""
        if risk_profile is None:
            return None
        normalized = risk_profile.strip().lower()
        return self.RISK_PROFILE_ALIASES.get(normalized, normalized)

    def _require_risk_profile(self, risk_profile: str) -> str:
        """Normalize and validate a required risk profile."""
        normalized = self._normalize_risk_profile(risk_profile)
        if normalized not in self.RISK_PROFILE_DEFAULTS:
            allowed = ", ".join(self.RISK_PROFILE_DEFAULTS)
            raise ValueError(
                f"Unknown risk profile: {risk_profile}. Allowed values: {allowed}"
            )
        return normalized

    def _normalize_timeframe(self, timeframe: Optional[str]) -> str:
        """Return a supported timeframe or the default fallback."""
        if not timeframe:
            return self.DEFAULT_TIMEFRAME
        normalized = timeframe.strip()
        if normalized not in self.BASE_MIN_TRADES_BY_TIMEFRAME:
            return self.DEFAULT_TIMEFRAME
        return normalized
