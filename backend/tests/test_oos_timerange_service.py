"""
Tests for Part 13 OOS timerange splitting.
"""
from datetime import date

import pytest

from app.services.oos_timerange_service import OOSTimerangeService


def test_valid_70_30_split():
    service = OOSTimerangeService()

    result = service.split_timerange("20240101-20240601")

    assert result == {
        "full_timerange": "20240101-20240601",
        "in_sample_timerange": "20240101-20240416",
        "out_of_sample_timerange": "20240416-20240601",
        "oos_ratio": 0.30,
        "total_days": 152,
        "in_sample_days": 106,
        "out_of_sample_days": 46,
        "warnings": [],
    }


def test_valid_60_40_split():
    service = OOSTimerangeService()

    result = service.split_timerange("20240101-20240601", oos_ratio=0.40)

    assert result["in_sample_timerange"] == "20240101-20240401"
    assert result["out_of_sample_timerange"] == "20240401-20240601"
    assert result["in_sample_days"] == 91
    assert result["out_of_sample_days"] == 61
    assert result["oos_ratio"] == 0.40


def test_valid_80_20_split():
    service = OOSTimerangeService()

    result = service.split_timerange("20240101-20240601", oos_ratio=0.20)

    assert result["in_sample_timerange"] == "20240101-20240501"
    assert result["out_of_sample_timerange"] == "20240501-20240601"
    assert result["in_sample_days"] == 121
    assert result["out_of_sample_days"] == 31
    assert result["oos_ratio"] == 0.20


@pytest.mark.parametrize(
    "timerange",
    [
        "",
        "20240101",
        "2024-01-01-2024-02-01",
        "20240101/20240201",
        "20241301-20240201",
    ],
)
def test_malformed_timerange_rejected(timerange):
    service = OOSTimerangeService()

    with pytest.raises(ValueError):
        service.parse_timerange(timerange)


def test_end_before_start_rejected():
    service = OOSTimerangeService()

    with pytest.raises(ValueError, match="after start"):
        service.parse_timerange("20240601-20240101")


def test_same_day_rejected():
    service = OOSTimerangeService()

    with pytest.raises(ValueError, match="after start"):
        service.parse_timerange("20240101-20240101")


def test_too_short_rejected():
    service = OOSTimerangeService()

    with pytest.raises(ValueError, match="too short"):
        service.split_timerange("20240101-20240115")


def test_unsupported_ratio_rejected():
    service = OOSTimerangeService()

    with pytest.raises(ValueError, match="0.20, 0.30, 0.40"):
        service.split_timerange("20240101-20240601", oos_ratio=0.25)


def test_deterministic_output():
    service = OOSTimerangeService()

    first = service.split_timerange("20240101-20240601", oos_ratio=0.30)
    second = service.split_timerange("20240101-20240601", oos_ratio=0.30)

    assert first == second


def test_oos_starts_at_or_after_is_end():
    service = OOSTimerangeService()

    result = service.split_timerange("20240101-20240601", oos_ratio=0.30)
    _, in_sample_end = service.parse_timerange(result["in_sample_timerange"])
    oos_start, _ = service.parse_timerange(result["out_of_sample_timerange"])

    assert oos_start >= in_sample_end
    assert oos_start == in_sample_end


def test_no_missing_dates():
    service = OOSTimerangeService()

    result = service.split_timerange("20240101-20240601", oos_ratio=0.40)
    full_start, full_end = service.parse_timerange(result["full_timerange"])
    in_start, in_end = service.parse_timerange(result["in_sample_timerange"])
    oos_start, oos_end = service.parse_timerange(result["out_of_sample_timerange"])

    assert in_start == full_start
    assert in_end == oos_start
    assert oos_end == full_end
    assert result["in_sample_days"] + result["out_of_sample_days"] == result["total_days"]


def test_build_from_days_works():
    service = OOSTimerangeService()

    result = service.build_from_days(100, oos_ratio=0.30)
    full_start, full_end = service.parse_timerange(result["full_timerange"])
    in_start, in_end = service.parse_timerange(result["in_sample_timerange"])
    oos_start, oos_end = service.parse_timerange(result["out_of_sample_timerange"])

    assert (full_end - full_start).days == 100
    assert in_start == full_start
    assert in_end == oos_start
    assert oos_end == full_end
    assert result["in_sample_days"] == 70
    assert result["out_of_sample_days"] == 30


def test_build_timerange_rejects_invalid_order():
    service = OOSTimerangeService()

    with pytest.raises(ValueError, match="after start"):
        service.build_timerange(date(2024, 2, 1), date(2024, 1, 1))


def test_validate_min_duration_can_use_timeframe_threshold():
    service = OOSTimerangeService()

    warnings = service.validate_min_duration(
        date(2024, 1, 1),
        date(2024, 3, 1),
        timeframe="4h",
    )

    assert warnings == ["timerange is too short: 60 days; minimum is 90 days"]
