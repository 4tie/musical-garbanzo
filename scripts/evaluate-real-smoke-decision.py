#!/usr/bin/env python3
"""
Validate Part 06 by evaluating an existing real smoke run's parsed evidence.

This script does not execute external trading tools, create fake runs, create
fake metrics, call model services, send notifications, or package strategies.
It only uses Part 05 evidence already saved in HER.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db.sqlite import fetch_all, initialize_database
from app.repositories.runs import RunRepository
from app.schemas.decisions import DecisionEvaluationRequest
from app.services.decision_service import DecisionService


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


def select_run_id(args) -> str | None:
    """Select run ID from CLI arguments or latest real smoke run."""
    if args.run_id:
        return args.run_id
    run = latest_smoke_run()
    return run["id"] if run else None


def reason_codes(decision) -> list[str]:
    """Return decision reason codes."""
    if not decision:
        return []
    return [reason.code for reason in decision.reasons]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a real smoke run using existing parsed HER evidence."
    )
    parser.add_argument("--run-id", help="Specific run ID to evaluate")
    parser.add_argument("--latest-smoke", action="store_true", help="Use latest real smoke run")
    parser.add_argument("--force", action="store_true", help="Replace previous decision rows for this run")
    parser.add_argument(
        "--risk-profile",
        choices=["balanced", "conservative", "aggressive"],
        default="balanced",
        help="Decision risk profile",
    )
    parser.add_argument(
        "--apply-to-run",
        action="store_true",
        help="Apply the safe decision classification to the run record",
    )
    args = parser.parse_args()

    initialize_database()

    run_id = select_run_id(args)
    if not run_id:
        print("REAL_DECISION_PENDING: run scripts/parse-real-smoke-backtest.py first")
        print_result("reason", "No real smoke run exists in SQLite")
        return 2

    run = RunRepository().get_run(run_id)
    if not run:
        print("REAL_DECISION_PENDING: run scripts/parse-real-smoke-backtest.py first")
        print_result("run_id", run_id)
        print_result("reason", "Run ID not found in SQLite")
        return 2

    response = DecisionService().evaluate_run(
        DecisionEvaluationRequest(
            run_id=run_id,
            risk_profile=args.risk_profile,
            timeframe=run.get("timeframe"),
            apply_to_run=args.apply_to_run,
            force=args.force,
        )
    )

    if not response.success and "parsed_metrics_missing" in response.errors:
        print("REAL_DECISION_PENDING: run scripts/parse-real-smoke-backtest.py first")
        print_result("run_id", run_id)
        print_result("risk_profile", args.risk_profile)
        print_result("errors", response.errors)
        return 2

    if not response.success:
        print("REAL_DECISION_FAILED")
        print_result("run_id", run_id)
        print_result("risk_profile", args.risk_profile)
        print_result("errors", response.errors)
        return 1

    decision = response.decision
    quality_flags = decision.evidence.quality_flags if decision else []
    reasons = reason_codes(decision)

    print_result("run_id", run_id)
    print_result("risk_profile", response.decision.risk_profile if response.decision else args.risk_profile)
    print_result("policy_name", response.policy_name)
    print_result("classification", response.classification)
    print_result("confidence_score", response.confidence_score)
    print_result("blocking_failures", response.blocking_failures)
    print_result("reasons", reasons)
    print_result("quality_flags", quality_flags)
    print_result("decision_report_path", response.decision_report_path)
    print_result("run_updated", response.run_updated)

    expected_blockers = {
        "negative_expectancy",
        "profit_factor_below_one",
        "drawdown_above_limit",
    }
    if response.classification == "rejected":
        missing = sorted(expected_blockers.difference(set(response.blocking_failures)))
        if missing:
            print_result("warning", f"Expected rejection blockers not all present: {missing}")
        print("REAL_DECISION_PASSED")
        return 0

    print("REAL_DECISION_FAILED_UNEXPECTED_CLASSIFICATION")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
