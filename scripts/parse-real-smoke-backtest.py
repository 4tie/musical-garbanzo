#!/usr/bin/env python3
"""
Validate Part 05 by parsing a real Part 04 Freqtrade smoke backtest output.

This script never runs Freqtrade, downloads data, calls Ollama, sends Discord
messages, or creates fake results. It only parses existing real smoke artifacts.
"""
import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db.sqlite import fetch_all, initialize_database
from app.repositories.runs import RunRepository
from app.services.backtest_result_parser import BacktestResultParser


SMOKE_RUN_NAME = "Real Freqtrade Smoke Test"


def print_result(key: str, value) -> None:
    """Print a stable key/value line for validation logs."""
    print(f"{key}: {value}")


def latest_smoke_run() -> dict | None:
    """Return the latest real smoke run row, if present."""
    rows = fetch_all(
        """
        SELECT * FROM runs
        WHERE name = ? AND COALESCE(is_demo, 0) = 0
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (SMOKE_RUN_NAME,),
    )
    return rows[0] if rows else None


def raw_artifacts_exist(run_id: str) -> bool:
    """Return whether a run has any raw Freqtrade artifact files."""
    raw_dir = PROJECT_ROOT / "artifacts" / "runs" / run_id / "raw_freqtrade"
    if not raw_dir.exists():
        return False
    return any(path.is_file() for path in raw_dir.rglob("*"))


def relative(path: str | None) -> str | None:
    """Return a project-relative path when possible."""
    if not path:
        return None
    try:
        return str(Path(path).resolve(strict=False).relative_to(PROJECT_ROOT))
    except ValueError:
        return path


def select_run_id(args) -> str | None:
    """Select run ID from CLI arguments or latest real smoke run."""
    if args.run_id:
        return args.run_id
    run = latest_smoke_run()
    return run["id"] if run else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a real Freqtrade smoke backtest result.")
    parser.add_argument("--run-id", help="Specific real smoke run ID to parse")
    parser.add_argument("--latest-smoke", action="store_true", help="Parse latest real smoke run")
    parser.add_argument("--force", action="store_true", help="Force reparse, replacing parser current-state rows")
    args = parser.parse_args()

    initialize_database()

    run_id = select_run_id(args)
    if not run_id:
        print("REAL_PARSE_PENDING: run scripts/freqtrade-real-smoke-test.py first")
        print_result("reason", "No real smoke run exists in SQLite")
        return 2

    run = RunRepository().get_run(run_id)
    if not run:
        print("REAL_PARSE_PENDING: run scripts/freqtrade-real-smoke-test.py first")
        print_result("run_id", run_id)
        print_result("reason", "Run ID not found in SQLite")
        return 2

    if run.get("name") != SMOKE_RUN_NAME:
        print("REAL_PARSE_FAILED")
        print_result("run_id", run_id)
        print_result("reason", f"Run is not named {SMOKE_RUN_NAME!r}")
        return 1

    if not raw_artifacts_exist(run_id):
        print("REAL_PARSE_PENDING: run scripts/freqtrade-real-smoke-test.py first")
        print_result("run_id", run_id)
        print_result("reason", "No raw Freqtrade artifacts found for run")
        return 2

    result = BacktestResultParser().parse_run(run_id, force=args.force)
    metrics = result.metrics.metrics if result.metrics and result.metrics.metrics else None
    source_files = []
    if result.loader:
        source_files = [relative(payload.source_path) for payload in result.loader.payloads]
    quality_flags = []
    if result.quality_report:
        quality_flags = [flag.code for flag in result.quality_report.flags]

    print_result("run_id", run_id)
    print_result("discovery_success", result.discovery.success if result.discovery else None)
    print_result("source_files", source_files)
    print_result("metrics_extracted", metrics is not None)
    print_result("trade_count", metrics.trade_count if metrics else None)
    print_result("net_profit", metrics.net_profit if metrics else None)
    print_result("profit_factor", metrics.profit_factor if metrics else None)
    print_result(
        "max_drawdown",
        (
            metrics.max_drawdown
            if metrics and metrics.max_drawdown is not None
            else metrics.max_drawdown_pct if metrics else None
        ),
    )
    print_result("expectancy", metrics.expectancy if metrics else None)
    print_result("pair_count", len(result.pair_results))
    print_result("quality_flags", quality_flags)
    print_result("normalized_artifact_path", relative(result.normalized_result_path))
    print_result("database_save_status", sorted(result.saved_records.keys()))

    if result.warnings:
        print_result("warnings", result.warnings)
    if result.errors:
        print_result("errors", result.errors)

    if result.success and metrics is not None and result.normalized_result_path:
        print("REAL_PARSE_PASSED")
        return 0

    print("REAL_PARSE_FAILED")
    print_result("reason", "Parser did not produce saved metrics and normalized artifact")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
