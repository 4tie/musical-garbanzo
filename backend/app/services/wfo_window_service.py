"""
Walk-forward window builder for Part 13 validation.

This service only generates deterministic date windows. It does not run
Hyperopt, run Freqtrade, add frontend behavior, or modify strategy files.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from app.schemas.validation import WFOWindowResult


class WFOWindowService:
    """Build walk-forward train/test windows from a full timerange."""

    TIMERANGE_PATTERN = re.compile(r"^\d{8}-\d{8}$")

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

    def build_windows(
        self,
        timerange,
        train_days,
        test_days,
        step_days,
        max_windows,
    ) -> list[WFOWindowResult]:
        """Build deterministic walk-forward windows."""
        errors = self.validate_wfo_config(
            timerange,
            train_days,
            test_days,
            step_days,
            max_windows,
        )
        if errors:
            raise ValueError("; ".join(errors))

        start, end = self.parse_timerange(timerange)
        train_days = int(train_days)
        test_days = int(test_days)
        step_days = int(step_days)
        max_windows = int(max_windows)

        windows: list[WFOWindowResult] = []
        train_start = start
        while len(windows) < max_windows:
            train_end = train_start + timedelta(days=train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=test_days)
            if test_end > end:
                break

            test_timerange = self.build_timerange(test_start, test_end)
            windows.append(
                WFOWindowResult(
                    window_index=len(windows) + 1,
                    timerange=test_timerange,
                    train_timerange=self.build_timerange(train_start, train_end),
                    test_timerange=test_timerange,
                    train_start=datetime.combine(train_start, datetime.min.time()),
                    train_end=datetime.combine(train_end, datetime.min.time()),
                    test_start=datetime.combine(test_start, datetime.min.time()),
                    test_end=datetime.combine(test_end, datetime.min.time()),
                    status="pending",
                )
            )
            train_start = train_start + timedelta(days=step_days)

        if not windows:
            raise ValueError("timerange is too short for one WFO train/test window")
        return windows

    def validate_wfo_config(
        self,
        timerange,
        train_days,
        test_days,
        step_days,
        max_windows,
    ) -> list[str]:
        """Return configuration errors for WFO window generation."""
        errors = []
        try:
            start, end = self.parse_timerange(timerange)
        except ValueError as exc:
            return [str(exc)]

        numeric_values = {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "max_windows": max_windows,
        }
        parsed = {}
        for field_name, value in numeric_values.items():
            try:
                parsed[field_name] = int(value)
            except (TypeError, ValueError):
                errors.append(f"{field_name} must be a positive integer")
                continue
            if parsed[field_name] <= 0:
                errors.append(f"{field_name} must be a positive integer")

        if errors:
            return errors

        if parsed["step_days"] < parsed["test_days"]:
            errors.append("step_days must be greater than or equal to test_days")

        total_days = (end - start).days
        required_days = parsed["train_days"] + parsed["test_days"]
        if total_days < required_days:
            errors.append(
                f"timerange is too short: {total_days} days; minimum is {required_days} days"
            )
        return errors
