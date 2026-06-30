"""
Out-of-sample timerange splitter for Part 13 validation.

This service is pure date arithmetic. It does not run Freqtrade, add frontend
behavior, modify strategy files, or inspect market data.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from math import ceil
from typing import Optional


class OOSTimerangeService:
    """Parse and split Freqtrade-style timeranges for OOS validation."""

    TIMERANGE_PATTERN = re.compile(r"^\d{8}-\d{8}$")
    SUPPORTED_OOS_RATIOS = {0.20, 0.30, 0.40}
    MIN_TOTAL_DAYS = 30
    MIN_IN_SAMPLE_DAYS = 14
    MIN_OUT_OF_SAMPLE_DAYS = 7

    TIMEFRAME_MIN_TOTAL_DAYS = {
        "1m": 14,
        "3m": 21,
        "5m": 30,
        "15m": 30,
        "30m": 45,
        "1h": 60,
        "2h": 75,
        "4h": 90,
        "1d": 180,
    }

    def parse_timerange(self, timerange: str) -> tuple[date, date]:
        """Parse a timerange in YYYYMMDD-YYYYMMDD format."""
        if not isinstance(timerange, str) or not self.TIMERANGE_PATTERN.match(timerange):
            raise ValueError("timerange must use YYYYMMDD-YYYYMMDD format")

        start_raw, end_raw = timerange.split("-", 1)
        try:
            start = datetime.strptime(start_raw, "%Y%m%d").date()
            end = datetime.strptime(end_raw, "%Y%m%d").date()
        except ValueError as exc:
            raise ValueError("timerange contains an invalid calendar date") from exc

        if end <= start:
            raise ValueError("timerange end date must be after start date")
        return start, end

    def build_timerange(self, start: date, end: date) -> str:
        """Build a timerange string in YYYYMMDD-YYYYMMDD format."""
        if end <= start:
            raise ValueError("timerange end date must be after start date")
        return f"{start:%Y%m%d}-{end:%Y%m%d}"

    def split_timerange(
        self,
        timerange: str,
        oos_ratio: float = 0.30,
    ) -> dict:
        """Split a full timerange into in-sample and out-of-sample ranges."""
        ratio = self._normalize_ratio(oos_ratio)
        start, end = self.parse_timerange(timerange)
        warnings = self.validate_min_duration(start, end)
        if warnings:
            raise ValueError("; ".join(warnings))

        total_days = (end - start).days
        out_of_sample_days = ceil(total_days * ratio)
        in_sample_days = total_days - out_of_sample_days
        if in_sample_days < self.MIN_IN_SAMPLE_DAYS or out_of_sample_days < self.MIN_OUT_OF_SAMPLE_DAYS:
            raise ValueError("timerange is too short for the requested OOS split")

        split_date = start + timedelta(days=in_sample_days)
        return {
            "full_timerange": self.build_timerange(start, end),
            "in_sample_timerange": self.build_timerange(start, split_date),
            "out_of_sample_timerange": self.build_timerange(split_date, end),
            "oos_ratio": ratio,
            "total_days": total_days,
            "in_sample_days": in_sample_days,
            "out_of_sample_days": out_of_sample_days,
            "warnings": [],
        }

    def build_from_days(
        self,
        days: int,
        oos_ratio: float = 0.30,
    ) -> dict:
        """Build a timerange ending today and split it into IS/OOS ranges."""
        if days <= 0:
            raise ValueError("days must be positive")
        end = date.today()
        start = end - timedelta(days=days)
        return self.split_timerange(self.build_timerange(start, end), oos_ratio=oos_ratio)

    def validate_min_duration(
        self,
        start,
        end,
        timeframe: Optional[str] = None,
    ) -> list[str]:
        """Return duration warnings that should block OOS splitting."""
        if end <= start:
            return ["timerange end date must be after start date"]

        total_days = (end - start).days
        min_total_days = self.TIMEFRAME_MIN_TOTAL_DAYS.get(
            str(timeframe or "").lower(),
            self.MIN_TOTAL_DAYS,
        )
        warnings = []
        if total_days < min_total_days:
            warnings.append(
                f"timerange is too short: {total_days} days; minimum is {min_total_days} days"
            )
        return warnings

    def _normalize_ratio(self, oos_ratio: float) -> float:
        """Validate and normalize supported OOS ratios."""
        try:
            ratio = round(float(oos_ratio), 2)
        except (TypeError, ValueError) as exc:
            raise ValueError("oos_ratio must be numeric") from exc

        if ratio not in self.SUPPORTED_OOS_RATIOS:
            raise ValueError("oos_ratio must be one of: 0.20, 0.30, 0.40")
        return ratio
