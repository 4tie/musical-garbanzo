"""
Tests for Part 13 validation execution service.

These tests mock Freqtrade-facing dependencies. They do not run Freqtrade,
approve strategies, export strategies, or call AI services.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.repositories.metrics import MetricsRepository
from app.repositories.optimization import OptimizationRepository
from app.repositories.runs import RunRepository
from app.repositories.validation import ValidationRepository
from app.schemas.metrics import MetricSnapshotCreate
from app.schemas.validation import ValidationRunRequest
from app.services.validation_execution_service import ValidationExecutionService


def make_request(**overrides) -> ValidationRunRequest:
    data = {
        "source_type": "strategy",
        "strategy_name": "SampleStrategy",
        "pairs": ["BTC/USDT", "ETH/USDT"],
        "timeframe": "15m",
        "exchange": "binance",
        "risk_profile": "balanced",
        "timerange": "20240101-20240601",
        "oos_ratio": 0.30,
        "wfo_train_days": 45,
        "wfo_test_days": 15,
        "wfo_step_days": 15,
        "wfo_max_windows": 2,
        "user_confirmed": True,
    }
    data.update(overrides)
    return ValidationRunRequest(**data)


def create_source_run_with_metrics(
    run_repo: RunRepository,
    metrics_repo: MetricsRepository,
) -> dict:
    run = run_repo.create_run(
        data=SimpleNamespace(
            name="source baseline",
            mode="manual_test",
            strategy_id=None,
            parent_run_id=None,
            exchange="binance",
            quote_currency="USDT",
            trading_mode="spot",
            timeframe="15m",
            pairs=["BTC/USDT", "ETH/USDT"],
            timerange="20240101-20240601",
            risk_profile="balanced",
            analysis_depth="baseline",
            is_demo=False,
        ),
        create_default_stages=False,
    )
    metrics_repo.create_metric_snapshot(
        MetricSnapshotCreate(
            run_id=run["id"],
            stage_key="backtest_result_parse",
            net_profit=100.0,
            profit_factor=1.8,
            max_drawdown=20.0,
            sharpe=1.2,
            calmar=1.0,
            win_rate=0.55,
            trade_count=100,
            expectancy=0.08,
            avg_win=2.0,
            avg_loss=-1.0,
            raw_json={"metrics": {"trade_count": 100}},
        )
    )
    return run


class RecordingReadinessGate:
    def __init__(self):
        self.calls = []

    def __call__(self, strategy_name, run_type="baseline"):
        self.calls.append({"strategy_name": strategy_name, "run_type": run_type})
        return SimpleNamespace(allowed=True)


class FakeConfigGenerator:
    def __init__(self, root: Path):
        self.root = root
        self.calls = []

    def write_backtest_config(self, request):
        self.calls.append(request)
        path = self.root / "configs" / f"{request.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return SimpleNamespace(success=True, config_path=str(path))


class FakeBacktestRunner:
    def __init__(self, fail_at_call: int | None = None):
        self.calls = []
        self.fail_at_call = fail_at_call

    def run_backtest(self, request):
        self.calls.append(request)
        if self.fail_at_call and len(self.calls) == self.fail_at_call:
            return SimpleNamespace(
                success=False,
                error="synthetic command failure",
                artifacts=[],
            )
        return SimpleNamespace(
            success=True,
            error=None,
            artifacts=[SimpleNamespace(path=f"artifacts/runs/{request.run_id}/raw.json")],
        )


class FakeParser:
    def __init__(self, metrics_queue):
        self.metrics_queue = list(metrics_queue)
        self.calls = []

    def parse_run(self, run_id, force=False):
        self.calls.append({"run_id": run_id, "force": force})
        metrics = self.metrics_queue.pop(0) if self.metrics_queue else {}
        return SimpleNamespace(
            success=True,
            metrics=SimpleNamespace(metrics=metrics),
            normalized_result_path=f"artifacts/runs/{run_id}/normalized.json",
            errors=[],
            warnings=[],
        )


class FakeDecisionService:
    def __init__(self):
        self.calls = []

    def evaluate_run(self, request):
        self.calls.append(request)
        return SimpleNamespace(
            model_dump=lambda mode="json", exclude=None: {
                "run_id": request.run_id,
                "success": True,
                "classification": "candidate",
                "warnings": [],
                "errors": [],
            }
        )


def make_service(tmp_path, metrics_queue, readiness_gate=None, runner=None):
    return ValidationExecutionService(
        validation_repository=ValidationRepository(),
        run_repository=RunRepository(),
        metrics_repository=MetricsRepository(),
        config_generator=FakeConfigGenerator(tmp_path),
        backtest_runner=runner or FakeBacktestRunner(),
        result_parser=FakeParser(metrics_queue),
        decision_service=FakeDecisionService(),
        readiness_gate=readiness_gate or RecordingReadinessGate(),
        project_root=tmp_path,
    )


def passing_metrics():
    return {"trade_count": 40, "profit_factor": 1.4, "expectancy": 0.06, "max_drawdown": 22.0}


def test_validation_execution_success_flow_uses_oos_wfo_robustness_and_report(tmp_path):
    run_repo = RunRepository()
    metrics_repo = MetricsRepository()
    source_run = create_source_run_with_metrics(run_repo, metrics_repo)
    readiness_gate = RecordingReadinessGate()
    runner = FakeBacktestRunner()
    service = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        run_repository=run_repo,
        metrics_repository=metrics_repo,
        config_generator=FakeConfigGenerator(tmp_path),
        backtest_runner=runner,
        result_parser=FakeParser([passing_metrics(), passing_metrics(), passing_metrics()]),
        decision_service=FakeDecisionService(),
        readiness_gate=readiness_gate,
        project_root=tmp_path,
    )

    response = service.run_validation(
        make_request(source_type="baseline_run", source_run_id=source_run["id"])
    )

    assert response.status == "completed"
    assert response.decision_status == "validated"
    assert readiness_gate.calls == [{"strategy_name": "SampleStrategy", "run_type": "validation"}]
    assert runner.calls[0].timerange == "20240416-20240601"
    assert [call.timerange for call in runner.calls[1:]] == [
        "20240215-20240301",
        "20240301-20240316",
    ]

    repo = ValidationRepository()
    evidence = repo.list_evidence(response.validation_run_id)
    assert {item["evidence_type"] for item in evidence} >= {
        "oos",
        "wfo_window",
        "wfo_summary",
        "robustness",
        "validation_decision",
    }

    run = repo.get_validation_run(response.validation_run_id)
    report_path = tmp_path / run["report_artifact_path"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["final_decision"]["decision_status"] == "validated"
    assert "guarantee of future performance" in report["no_guarantee_statement"]
    assert "stdout" not in json.dumps(report).lower()
    assert "stderr" not in json.dumps(report).lower()


def test_user_confirmed_false_blocks_real_validation(tmp_path):
    readiness_gate = RecordingReadinessGate()
    runner = FakeBacktestRunner()
    service = make_service(tmp_path, [passing_metrics()], readiness_gate, runner)

    response = service.run_validation(make_request(user_confirmed=False))

    assert response.status == "confirmation_required"
    assert response.decision_status == "not_validated"
    assert readiness_gate.calls
    assert runner.calls == []


def test_oos_timerange_split_used_and_backtest_receives_only_oos_timerange(tmp_path):
    runner = FakeBacktestRunner()
    service = make_service(tmp_path, [passing_metrics()], runner=runner)

    response = service.run_validation(make_request(wfo_enabled=False, robustness_enabled=False))

    assert response.status == "completed"
    assert runner.calls[0].timerange == "20240416-20240601"
    assert runner.calls[0].timerange != "20240101-20240601"


def test_missing_metrics_are_rejected_without_fake_values(tmp_path):
    service = make_service(tmp_path, [{}])

    response = service.run_validation(make_request(wfo_enabled=False))

    assert response.status == "completed"
    assert response.decision_status == "rejected"
    evidence = ValidationRepository().list_evidence(response.validation_run_id)
    oos = next(item for item in evidence if item["evidence_type"] == "oos")
    assert oos["status"] == "oos_failed"
    encoded = json.dumps(evidence).lower()
    assert "fake" not in encoded


def test_no_live_export_approval_or_secret_wording_in_response(tmp_path):
    service = make_service(tmp_path, [passing_metrics()])

    response = service.run_validation(make_request(wfo_enabled=False, robustness_enabled=False))
    payload = response.model_dump(mode="json")
    encoded = json.dumps(payload).lower()

    assert "live trading" not in encoded
    assert "approved for live" not in encoded
    assert "api_key" not in encoded
    assert "secret" not in encoded
    assert "token" not in encoded


def test_enabled_sensitivity_failure_rejects_final_decision(tmp_path):
    run_repo = RunRepository()
    metrics_repo = MetricsRepository()
    source_run = create_source_run_with_metrics(run_repo, metrics_repo)
    service = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        run_repository=run_repo,
        metrics_repository=metrics_repo,
        config_generator=FakeConfigGenerator(tmp_path),
        backtest_runner=FakeBacktestRunner(),
        result_parser=FakeParser([passing_metrics()]),
        decision_service=FakeDecisionService(),
        readiness_gate=RecordingReadinessGate(),
        project_root=tmp_path,
    )

    response = service.run_validation(
        make_request(
            source_type="baseline_run",
            source_run_id=source_run["id"],
            wfo_enabled=False,
            sensitivity_enabled=True,
        )
    )

    assert response.status == "completed"
    assert response.decision_status == "rejected"
    evidence = ValidationRepository().list_evidence(response.validation_run_id)
    sensitivity = [item for item in evidence if item["evidence_type"] == "sensitivity"]
    assert sensitivity


def test_optimization_run_source_uses_optimized_run_id(tmp_path):
    """Test that optimization_run source type loads from OptimizationRepository and uses optimized_run_id."""
    run_repo = RunRepository()
    metrics_repo = MetricsRepository()
    opt_repo = OptimizationRepository()

    # Create baseline run
    baseline_run = run_repo.create_run(
        data=SimpleNamespace(
            name="baseline",
            mode="manual_test",
            strategy_id="TestStrategy",
            parent_run_id=None,
            exchange="binance",
            quote_currency="USDT",
            trading_mode="spot",
            timeframe="15m",
            pairs=["BTC/USDT"],
            timerange="20240101-20240601",
            risk_profile="balanced",
            analysis_depth="baseline",
            is_demo=False,
        ),
        create_default_stages=False,
    )

    # Create optimized run
    optimized_run = run_repo.create_run(
        data=SimpleNamespace(
            name="optimized",
            mode="manual_test",
            strategy_id="TestStrategy",
            parent_run_id=baseline_run["id"],
            exchange="binance",
            quote_currency="USDT",
            trading_mode="spot",
            timeframe="15m",
            pairs=["BTC/USDT"],
            timerange="20240101-20240601",
            risk_profile="balanced",
            analysis_depth="baseline",
            is_demo=False,
        ),
        create_default_stages=False,
    )

    # Add metrics to optimized run
    metrics_repo.create_metric_snapshot(
        MetricSnapshotCreate(
            run_id=optimized_run["id"],
            stage_key="backtest_result_parse",
            net_profit=150.0,
            profit_factor=2.0,
            max_drawdown=15.0,
            sharpe=1.5,
            calmar=1.2,
            win_rate=0.60,
            trade_count=120,
            expectancy=0.10,
            avg_win=2.5,
            avg_loss=-1.2,
            raw_json={"metrics": {"trade_count": 120}},
        )
    )

    # Create optimization run with optimized_run_id
    optimization_run = opt_repo.create_optimization_run(
        {
            "id": "opt-test-123",
            "parent_run_id": baseline_run["id"],
            "baseline_run_id": baseline_run["id"],
            "optimized_run_id": optimized_run["id"],
            "strategy_name": "TestStrategy",
            "timeframe": "15m",
            "pairs": ["BTC/USDT"],
            "exchange": "binance",
            "risk_profile": "balanced",
            "status": "completed",
            "result_status": "success",
            "best_trial_id": "trial-1",
            "epochs_requested": 10,
            "epochs_completed": 10,
        }
    )

    service = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        run_repository=run_repo,
        metrics_repository=metrics_repo,
        optimization_repository=opt_repo,
        config_generator=FakeConfigGenerator(tmp_path),
        backtest_runner=FakeBacktestRunner(),
        result_parser=FakeParser([passing_metrics()]),
        decision_service=FakeDecisionService(),
        readiness_gate=RecordingReadinessGate(),
        project_root=tmp_path,
    )

    request = make_request(
        source_type="optimization_run",
        source_run_id=optimization_run["id"],
        wfo_enabled=False,
        robustness_enabled=False,
    )

    candidate = service._build_candidate_reference(request)

    # Verify candidate uses optimized run data
    assert candidate["source_run_id"] == optimized_run["id"]
    assert candidate["optimization_run_id"] == optimization_run["id"]
    assert candidate["baseline_run_id"] == baseline_run["id"]
    assert candidate["best_trial_id"] == "trial-1"
    assert candidate["optimized_run_id"] == optimized_run["id"]
    assert candidate["strategy_name"] == "TestStrategy"
    assert candidate["pairs"] == ["BTC/USDT"]
    assert candidate["timeframe"] == "15m"
    assert candidate["metrics"]["trade_count"] == 120


def test_optimization_run_not_found_controlled_failure(tmp_path):
    """Test that missing optimization run returns controlled failure."""
    run_repo = RunRepository()
    opt_repo = OptimizationRepository()

    service = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        run_repository=run_repo,
        metrics_repository=MetricsRepository(),
        optimization_repository=opt_repo,
        project_root=tmp_path,
    )

    request = make_request(
        source_type="optimization_run",
        source_run_id="nonexistent-opt-run",
    )

    try:
        service._build_candidate_reference(request)
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "optimization_run_not_found" in str(exc)


def test_optimized_run_missing_controlled_failure(tmp_path):
    """Test that missing optimized_run_id returns controlled failure."""
    run_repo = RunRepository()
    opt_repo = OptimizationRepository()

    # Create optimization run without optimized_run_id
    optimization_run = opt_repo.create_optimization_run(
        {
            "id": "opt-test-456",
            "parent_run_id": None,
            "baseline_run_id": None,
            "optimized_run_id": None,  # Missing
            "strategy_name": "TestStrategy",
            "timeframe": "15m",
            "pairs": ["BTC/USDT"],
            "exchange": "binance",
            "risk_profile": "balanced",
            "status": "completed",
            "result_status": "success",
        }
    )

    service = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        run_repository=run_repo,
        metrics_repository=MetricsRepository(),
        optimization_repository=opt_repo,
        project_root=tmp_path,
    )

    request = make_request(
        source_type="optimization_run",
        source_run_id=optimization_run["id"],
    )

    try:
        service._build_candidate_reference(request)
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "optimized_run_missing" in str(exc)


def test_optimized_run_missing_metrics_warning(tmp_path):
    """Test that optimized run with no metrics adds warning."""
    run_repo = RunRepository()
    metrics_repo = MetricsRepository()
    opt_repo = OptimizationRepository()

    # Create optimized run without metrics
    optimized_run = run_repo.create_run(
        data=SimpleNamespace(
            name="optimized",
            mode="manual_test",
            strategy_id="TestStrategy",
            parent_run_id=None,
            exchange="binance",
            quote_currency="USDT",
            trading_mode="spot",
            timeframe="15m",
            pairs=["BTC/USDT"],
            timerange="20240101-20240601",
            risk_profile="balanced",
            analysis_depth="baseline",
            is_demo=False,
        ),
        create_default_stages=False,
    )

    # Create optimization run with optimized_run_id
    optimization_run = opt_repo.create_optimization_run(
        {
            "id": "opt-test-789",
            "optimized_run_id": optimized_run["id"],
            "strategy_name": "TestStrategy",
            "timeframe": "15m",
            "pairs": ["BTC/USDT"],
            "exchange": "binance",
            "risk_profile": "balanced",
            "status": "completed",
            "result_status": "success",
        }
    )

    service = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        run_repository=run_repo,
        metrics_repository=metrics_repo,
        optimization_repository=opt_repo,
        project_root=tmp_path,
    )

    request = make_request(
        source_type="optimization_run",
        source_run_id=optimization_run["id"],
    )

    candidate = service._build_candidate_reference(request)

    # Verify warning is added
    assert "warnings" in candidate
    assert any("optimized_source_metrics_missing" in w for w in candidate["warnings"])
    assert candidate["metrics"] == {}
