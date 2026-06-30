"""
Tests for Part 13 WFO window generation.
"""
import pytest

from app.services.wfo_window_service import WFOWindowService


def test_valid_windows():
    service = WFOWindowService()

    windows = service.build_windows(
        "20240101-20240601",
        train_days=60,
        test_days=30,
        step_days=30,
        max_windows=5,
    )

    assert len(windows) == 3
    assert windows[0].window_index == 1
    assert windows[0].train_timerange == "20240101-20240301"
    assert windows[0].test_timerange == "20240301-20240331"
    assert windows[0].timerange == windows[0].test_timerange
    assert windows[0].status == "pending"
    assert windows[1].train_timerange == "20240131-20240331"
    assert windows[1].test_timerange == "20240331-20240430"
    assert windows[2].train_timerange == "20240301-20240430"
    assert windows[2].test_timerange == "20240430-20240530"


def test_too_short_range_rejected():
    service = WFOWindowService()

    with pytest.raises(ValueError, match="too short"):
        service.build_windows(
            "20240101-20240201",
            train_days=60,
            test_days=30,
            step_days=30,
            max_windows=5,
        )


def test_max_windows_respected():
    service = WFOWindowService()

    windows = service.build_windows(
        "20240101-20240901",
        train_days=60,
        test_days=30,
        step_days=30,
        max_windows=2,
    )

    assert len(windows) == 2
    assert [window.window_index for window in windows] == [1, 2]


def test_step_days_works():
    service = WFOWindowService()

    windows = service.build_windows(
        "20240101-20240801",
        train_days=60,
        test_days=20,
        step_days=40,
        max_windows=5,
    )

    assert windows[0].train_timerange == "20240101-20240301"
    assert windows[0].test_timerange == "20240301-20240321"
    assert windows[1].train_timerange == "20240210-20240410"
    assert windows[1].test_timerange == "20240410-20240430"
    assert windows[2].train_timerange == "20240321-20240520"
    assert windows[2].test_timerange == "20240520-20240609"


def test_train_test_order_correct():
    service = WFOWindowService()

    windows = service.build_windows(
        "20240101-20240601",
        train_days=60,
        test_days=30,
        step_days=30,
        max_windows=5,
    )

    for window in windows:
        assert window.train_start < window.train_end
        assert window.train_end == window.test_start
        assert window.test_start < window.test_end


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
    service = WFOWindowService()

    with pytest.raises(ValueError):
        service.parse_timerange(timerange)


def test_end_before_start_rejected():
    service = WFOWindowService()

    with pytest.raises(ValueError, match="after start"):
        service.parse_timerange("20240601-20240101")


def test_test_windows_do_not_overlap():
    service = WFOWindowService()

    windows = service.build_windows(
        "20240101-20240801",
        train_days=60,
        test_days=20,
        step_days=20,
        max_windows=5,
    )

    for previous, current in zip(windows, windows[1:]):
        assert previous.test_end <= current.test_start


def test_deterministic_output():
    service = WFOWindowService()
    args = {
        "timerange": "20240101-20240801",
        "train_days": 60,
        "test_days": 20,
        "step_days": 20,
        "max_windows": 5,
    }

    first = [window.model_dump(mode="json") for window in service.build_windows(**args)]
    second = [window.model_dump(mode="json") for window in service.build_windows(**args)]

    assert first == second


def test_invalid_config_rejected():
    service = WFOWindowService()

    errors = service.validate_wfo_config(
        "20240101-20240601",
        train_days=0,
        test_days=-1,
        step_days=10,
        max_windows=0,
    )

    assert "train_days must be a positive integer" in errors
    assert "test_days must be a positive integer" in errors
    assert "max_windows must be a positive integer" in errors


def test_step_shorter_than_test_rejected_to_prevent_overlap():
    service = WFOWindowService()

    errors = service.validate_wfo_config(
        "20240101-20240601",
        train_days=60,
        test_days=30,
        step_days=15,
        max_windows=5,
    )

    assert "step_days must be greater than or equal to test_days" in errors


def test_build_timerange_rejects_invalid_order():
    service = WFOWindowService()

    with pytest.raises(ValueError, match="after start"):
        service.build_timerange(
            service.parse_timerange("20240101-20240201")[1],
            service.parse_timerange("20240101-20240201")[0],
        )
