"""
Tests for Part 13 validation evidence repository.
"""
from app.db.sqlite import fetch_all, fetch_one
from app.repositories.validation import ValidationRepository


def make_run_data(**overrides):
    data = {
        "source_type": "strategy",
        "source_run_id": None,
        "strategy_name": "SmokeTestStrategy",
        "timeframe": "5m",
        "pairs": ["BTC/USDT", "ETH/USDT"],
        "exchange": "binance",
        "risk_profile": "balanced",
        "status": "pending",
        "decision_status": "not_validated",
        "timerange": "20250101-20250331",
        "oos_timerange": "20250301-20250331",
        "wfo_config": {"train_days": 60, "test_days": 15, "max_windows": 3},
        "policy": {"policy_name": "default_validation_policy"},
        "request": {"user_confirmed": False, "download_missing_data": False},
        "summary": {"evidence_count": 0},
    }
    data.update(overrides)
    return data


def make_evidence_data(validation_run_id: str, **overrides):
    data = {
        "validation_run_id": validation_run_id,
        "evidence_type": "oos",
        "status": "completed",
        "timerange": "20250301-20250331",
        "metrics": {"profit_factor": 1.4, "trade_count": 22},
        "decision": {"classification": "candidate"},
        "issues": [],
        "warnings": ["low_trade_count_warning"],
        "artifact_paths": [
            "artifacts/runs/validation-run/oos/backtest_result.normalized.json"
        ],
    }
    data.update(overrides)
    return data


def test_migrations_create_validation_tables_and_indexes():
    tables = fetch_all(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name IN ('validation_runs', 'validation_evidence')
        ORDER BY name
        """
    )
    table_names = [table["name"] for table in tables]

    indexes = fetch_all(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'index' AND name LIKE 'idx_validation_%'
        """
    )
    index_names = {index["name"] for index in indexes}

    assert table_names == ["validation_evidence", "validation_runs"]
    assert "idx_validation_runs_strategy_name" in index_names
    assert "idx_validation_runs_status" in index_names
    assert "idx_validation_runs_decision_status" in index_names
    assert "idx_validation_runs_created_at" in index_names
    assert "idx_validation_evidence_run_id" in index_names
    assert "idx_validation_evidence_type" in index_names
    assert "idx_validation_evidence_status" in index_names
    assert "idx_validation_evidence_window_index" in index_names


def test_create_validation_run_round_trips_json():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())

    assert run["id"]
    assert run["source_type"] == "strategy"
    assert run["strategy_name"] == "SmokeTestStrategy"
    assert run["pairs"] == ["BTC/USDT", "ETH/USDT"]
    assert run["wfo_config"]["train_days"] == 60
    assert run["policy"]["policy_name"] == "default_validation_policy"
    assert run["request"]["user_confirmed"] is False
    assert run["summary"]["evidence_count"] == 0
    assert run["created_at"]
    assert run["updated_at"]


def test_update_validation_run():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())

    updated = repo.update_validation_run(
        run["id"],
        {
            "status": "running",
            "decision_status": "oos_passed",
            "summary": {"evidence_count": 1},
            "report_artifact_path": "artifacts/runs/validation-run/validation/report.json",
        },
    )

    assert updated["status"] == "running"
    assert updated["decision_status"] == "oos_passed"
    assert updated["summary"] == {"evidence_count": 1}
    assert updated["report_artifact_path"].endswith("report.json")


def test_list_validation_runs_with_filters():
    repo = ValidationRepository()
    repo.create_validation_run(make_run_data(strategy_name="ValidationListA"))
    repo.create_validation_run(
        make_run_data(
            strategy_name="ValidationListB",
            source_type="baseline_run",
            status="completed",
            decision_status="validated",
        )
    )

    completed = repo.list_validation_runs(status="completed")
    validated = repo.list_validation_runs(decision_status="validated")
    baseline_sources = repo.list_validation_runs(source_type="baseline_run")

    assert any(run["strategy_name"] == "ValidationListB" for run in completed)
    assert any(run["decision_status"] == "validated" for run in validated)
    assert all(run["source_type"] == "baseline_run" for run in baseline_sources)


def test_create_oos_evidence():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())
    evidence = repo.create_evidence(make_evidence_data(run["id"]))

    assert evidence["id"]
    assert evidence["validation_run_id"] == run["id"]
    assert evidence["evidence_type"] == "oos"
    assert evidence["metrics"]["profit_factor"] == 1.4
    assert evidence["warnings"] == ["low_trade_count_warning"]
    assert evidence["artifact_paths"][0].startswith("artifacts/runs/")


def test_create_wfo_evidence():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())
    evidence = repo.create_evidence(
        make_evidence_data(
            run["id"],
            evidence_type="wfo_window",
            status="wfo_passed",
            window_index=2,
            timerange="20250215-20250301",
            metrics={"profit_factor": 1.2, "trade_count": 18},
        )
    )

    assert evidence["evidence_type"] == "wfo_window"
    assert evidence["status"] == "wfo_passed"
    assert evidence["window_index"] == 2
    assert evidence["metrics"]["trade_count"] == 18


def test_create_robustness_evidence():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())
    evidence = repo.create_evidence(
        make_evidence_data(
            run["id"],
            evidence_type="robustness",
            status="robustness_passed",
            metrics={"pair_subset_count": 2},
            issues=[{"code": "pair_subset_ok", "message": "Pair subset passed"}],
        )
    )

    assert evidence["evidence_type"] == "robustness"
    assert evidence["status"] == "robustness_passed"
    assert evidence["issues"][0]["code"] == "pair_subset_ok"


def test_bulk_create_evidence_and_list_order():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())
    created = repo.bulk_create_evidence(
        [
            make_evidence_data(run["id"], evidence_type="wfo_window", window_index=1),
            make_evidence_data(run["id"], evidence_type="wfo_window", window_index=0),
            make_evidence_data(run["id"], evidence_type="wfo_summary", status="wfo_passed"),
        ]
    )
    listed = repo.list_evidence(run["id"], evidence_type="wfo_window")

    assert len(created) == 3
    assert [item["window_index"] for item in listed] == [0, 1]


def test_save_and_get_decision():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())
    decision = {
        "decision_status": "validated",
        "reasons": ["OOS, WFO, and robustness passed"],
        "warnings": [],
    }

    updated = repo.save_decision(run["id"], decision)
    saved_decision = repo.get_decision(run["id"])

    assert updated["decision_status"] == "validated"
    assert saved_decision == decision


def test_get_evidence_returns_none_for_missing_id():
    repo = ValidationRepository()

    assert repo.get_evidence("not-a-real-evidence-id") is None


def test_validation_rows_are_raw_json_in_database_but_serialized_for_api():
    repo = ValidationRepository()
    run = repo.create_validation_run(make_run_data())
    repo.create_evidence(make_evidence_data(run["id"]))

    raw_run = fetch_one("SELECT pairs_json FROM validation_runs WHERE id = ?", (run["id"],))
    raw_evidence = fetch_one(
        "SELECT metrics_json FROM validation_evidence WHERE validation_run_id = ?",
        (run["id"],),
    )
    serialized = repo.get_validation_run(run["id"])
    evidence = repo.list_evidence(run["id"])[0]

    assert raw_run["pairs_json"].startswith("[")
    assert raw_evidence["metrics_json"].startswith("{")
    assert serialized["pairs"] == ["BTC/USDT", "ETH/USDT"]
    assert evidence["metrics"]["profit_factor"] == 1.4
