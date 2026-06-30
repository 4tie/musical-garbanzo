"""
Tests for raw Freqtrade backtest result loading.
"""
import zipfile
from pathlib import Path

from app.schemas.backtest_results import (
    BacktestOutputDiscoveryResult,
    BacktestOutputFile,
)
from app.services.backtest_result_loader import BacktestResultLoader


def make_loader(tmp_path: Path) -> BacktestResultLoader:
    """Build a loader rooted in a temp project."""
    return BacktestResultLoader(project_root=tmp_path)


def make_output_file(path: Path, file_type: str) -> BacktestOutputFile:
    """Build a discovered output file model for loader tests."""
    stat_result = path.stat()
    return BacktestOutputFile(
        path=str(path.resolve()),
        relative_path=path.name,
        file_name=path.name,
        file_type=file_type,
        size_bytes=stat_result.st_size,
        modified_at="2026-01-01T00:00:00+00:00",
        source="backtest_results_dir",
        is_candidate_result=file_type in {"json", "zip"},
    )


def test_load_valid_json(tmp_path):
    """Valid JSON loads into raw_data."""
    result_file = tmp_path / "backtest-result.json"
    result_file.write_text('{"strategy": {"HERSmokeStrategy": {}}}')

    payload = make_loader(tmp_path).load_json(result_file)

    assert payload.raw_data == {"strategy": {"HERSmokeStrategy": {}}}
    assert payload.raw_text is None
    assert payload.parser_type == "freqtrade_json"
    assert payload.errors == []


def test_malformed_json_returns_controlled_error(tmp_path):
    """Malformed JSON is returned as a controlled payload error."""
    result_file = tmp_path / "backtest-result.json"
    result_file.write_text('{"strategy": ')

    payload = make_loader(tmp_path).load_json(result_file)

    assert payload.raw_data is None
    assert payload.errors
    assert payload.errors[0].startswith("json_load_error:")


def test_load_zip_with_json_member(tmp_path):
    """ZIP JSON members are loaded without extraction."""
    result_file = tmp_path / "backtest-result.zip"
    with zipfile.ZipFile(result_file, "w") as archive:
        archive.writestr("results/backtest.json", '{"strategy": {"HERSmokeStrategy": {}}}')

    payloads = make_loader(tmp_path).load_zip(result_file)

    assert len(payloads) == 1
    assert payloads[0].raw_data == {"strategy": {"HERSmokeStrategy": {}}}
    assert payloads[0].zip_members == ["results/backtest.json"]
    assert payloads[0].errors == []


def test_zip_with_unsafe_member_is_ignored(tmp_path):
    """Unsafe ZIP members are ignored and not extracted."""
    result_file = tmp_path / "backtest-result.zip"
    with zipfile.ZipFile(result_file, "w") as archive:
        archive.writestr("../unsafe.json", '{"strategy": {}}')
        archive.writestr("/absolute.json", '{"strategy": {}}')
        archive.writestr("safe/backtest.json", '{"strategy": {"HERSmokeStrategy": {}}}')

    members = make_loader(tmp_path).find_json_members_in_zip(result_file)
    payloads = make_loader(tmp_path).load_zip(result_file)

    assert members == ["safe/backtest.json"]
    assert len(payloads) == 1
    assert payloads[0].raw_data == {"strategy": {"HERSmokeStrategy": {}}}
    assert not (tmp_path.parent / "unsafe.json").exists()


def test_zip_with_no_json_returns_warning(tmp_path):
    """ZIPs with no JSON members return a warning payload."""
    result_file = tmp_path / "backtest-result.zip"
    with zipfile.ZipFile(result_file, "w") as archive:
        archive.writestr("notes.txt", "not json")

    payloads = make_loader(tmp_path).load_zip(result_file)

    assert len(payloads) == 1
    assert payloads[0].raw_data is None
    assert "zip_no_json_members" in payloads[0].warnings
    assert payloads[0].errors == []


def test_stdout_fallback_loads_text(tmp_path):
    """stdout.log loads as fallback text."""
    stdout = tmp_path / "stdout.log"
    stdout.write_text("BACKTESTING REPORT")

    payload = make_loader(tmp_path).load_stdout(stdout)

    assert payload.raw_text == "BACKTESTING REPORT"
    assert payload.parser_type == "stdout_table_fallback"
    assert "stdout_fallback_only" in payload.warnings
    assert payload.raw_data is None


def test_too_large_file_rejected(tmp_path):
    """Oversized input reads are rejected safely."""
    result_file = tmp_path / "large.log"
    result_file.write_text("abcdef")

    try:
        make_loader(tmp_path).safe_read_text(result_file, max_bytes=3)
    except ValueError as exc:
        assert "file_too_large" in str(exc)
    else:
        raise AssertionError("Expected oversized file rejection")


def test_outside_project_root_rejected(tmp_path):
    """Files outside project root are rejected before reading."""
    outside = tmp_path.parent / "outside-result.json"
    outside.write_text('{"strategy": {}}')

    payload = make_loader(tmp_path).load_json(outside)

    assert payload.raw_data is None
    assert payload.errors
    assert "path_outside_project_root" in payload.errors[0]


def test_env_file_rejected(tmp_path):
    """The loader explicitly rejects .env files."""
    env_file = tmp_path / ".env"
    env_file.write_text("APP_SECRET_KEY=secret")

    payload = make_loader(tmp_path).load_file(env_file)

    assert not isinstance(payload, list)
    assert payload.raw_data is None
    assert payload.raw_text is None
    assert "env_file_rejected" in payload.errors


def test_database_file_rejected(tmp_path):
    """The loader explicitly rejects database files as result inputs."""
    db_file = tmp_path / "her.db"
    db_file.write_bytes(b"SQLite format 3")

    payload = make_loader(tmp_path).load_file(db_file)

    assert not isinstance(payload, list)
    assert "database_file_rejected" in payload.errors


def test_primary_payload_selection_prefers_json_over_stdout(tmp_path):
    """Primary payload selection prefers structured JSON over stdout text."""
    json_file = tmp_path / "backtest-result.json"
    stdout = tmp_path / "stdout.log"
    json_file.write_text('{"strategy": {"HERSmokeStrategy": {}}}')
    stdout.write_text("BACKTESTING REPORT")

    loader = make_loader(tmp_path)
    json_payload = loader.load_json(json_file)
    stdout_payload = loader.load_stdout(stdout)

    primary = loader.select_primary_payload([stdout_payload, json_payload])

    assert primary == json_payload


def test_load_from_discovery_prefers_primary_json(tmp_path):
    """Loading from discovery chooses structured primary payload."""
    json_file = tmp_path / "backtest-result.json"
    stdout = tmp_path / "stdout.log"
    json_file.write_text('{"strategy": {"HERSmokeStrategy": {}}}')
    stdout.write_text("BACKTESTING REPORT")
    discovery = BacktestOutputDiscoveryResult(
        run_id="run-123",
        success=True,
        primary_result_path=str(json_file.resolve()),
        stdout_path=str(stdout.resolve()),
        files=[
            make_output_file(stdout, "stdout_log"),
            make_output_file(json_file, "json"),
        ],
    )

    result = make_loader(tmp_path).load_from_discovery(discovery)

    assert result.success is True
    assert result.primary_payload is not None
    assert result.primary_payload.source_path == str(json_file.resolve())
    assert len(result.payloads) == 2
