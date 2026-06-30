"""
Tests for Part 08 optimization repository.
"""
import pytest
from app.repositories.optimization import OptimizationRepository
from app.core.constants import (
    OPTIMIZATION_STATUSES,
    OPTIMIZATION_RESULT_STATUSES,
    OPTIMIZATION_TRIAL_STATUSES,
)


@pytest.fixture
def repo():
    """Create an OptimizationRepository instance."""
    return OptimizationRepository()


@pytest.fixture
def sample_run_data():
    """Sample optimization run data."""
    return {
        "strategy_name": "TestStrategy",
        "timeframe": "5m",
        "pairs": ["BTC/USDT", "ETH/USDT"],
        "exchange": "binance",
        "risk_profile": "balanced",
        "status": "pending",
        "epochs_requested": 50,
        "spaces": ["buy", "sell"],
        "request": {"user_confirmed": False},
    }


@pytest.fixture
def sample_trial_data():
    """Sample trial data."""
    return {
        "optimization_run_id": "test-run-id",
        "trial_number": 1,
        "status": "completed",
        "is_best": False,
        "params": {"buy": {"rsi": 30}, "sell": {"rsi": 70}},
        "buy_params": {"rsi": 30},
        "sell_params": {"rsi": 70},
        "metrics": {"profit_total": 100.0, "profit_factor": 1.5},
        "loss_score": 0.5,
        "profit_total": 100.0,
        "profit_factor": 1.5,
        "trade_count": 50,
        "win_rate": 0.6,
    }


class TestOptimizationRepository:
    """Test OptimizationRepository methods."""

    def test_create_optimization_run(self, repo, sample_run_data):
        """Test creating an optimization run."""
        run = repo.create_optimization_run(sample_run_data)

        assert run is not None
        assert run["id"] is not None
        assert run["strategy_name"] == "TestStrategy"
        assert run["timeframe"] == "5m"
        assert run["pairs"] == ["BTC/USDT", "ETH/USDT"]
        assert run["status"] == "pending"
        assert run["epochs_requested"] == 50
        assert run["spaces"] == ["buy", "sell"]
        assert run["created_at"] is not None
        assert run["updated_at"] is not None

    def test_get_optimization_run(self, repo, sample_run_data):
        """Test getting an optimization run by ID."""
        created = repo.create_optimization_run(sample_run_data)
        retrieved = repo.get_optimization_run(created["id"])

        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["strategy_name"] == created["strategy_name"]

    def test_update_optimization_run(self, repo, sample_run_data):
        """Test updating an optimization run."""
        created = repo.create_optimization_run(sample_run_data)

        updated = repo.update_optimization_run(
            created["id"],
            {
                "status": "running",
                "epochs_completed": 25,
                "result_status": "improved",
            },
        )

        assert updated is not None
        assert updated["status"] == "running"
        assert updated["epochs_completed"] == 25
        assert updated["result_status"] == "improved"

    def test_list_optimization_runs(self, repo, sample_run_data):
        """Test listing optimization runs."""
        # Create multiple runs
        repo.create_optimization_run(sample_run_data)
        repo.create_optimization_run(
            {
                **sample_run_data,
                "strategy_name": "AnotherStrategy",
                "status": "completed",
            }
        )

        runs = repo.list_optimization_runs()

        assert len(runs) >= 2
        assert any(r["strategy_name"] == "TestStrategy" for r in runs)
        assert any(r["strategy_name"] == "AnotherStrategy" for r in runs)

    def test_list_optimization_runs_with_filters(self, repo, sample_run_data):
        """Test listing optimization runs with filters."""
        repo.create_optimization_run(sample_run_data)
        repo.create_optimization_run(
            {**sample_run_data, "strategy_name": "TestStrategy", "status": "completed"}
        )

        pending_runs = repo.list_optimization_runs(status="pending")
        completed_runs = repo.list_optimization_runs(status="completed")

        assert len(pending_runs) >= 1
        assert all(r["status"] == "pending" for r in pending_runs)
        assert len(completed_runs) >= 1
        assert all(r["status"] == "completed" for r in completed_runs)

    def test_create_trial(self, repo, sample_run_data, sample_trial_data):
        """Test creating a single trial."""
        # First create a run
        run = repo.create_optimization_run(sample_run_data)
        sample_trial_data["optimization_run_id"] = run["id"]

        trial = repo.create_trial(sample_trial_data)

        assert trial is not None
        assert trial["id"] is not None
        assert trial["optimization_run_id"] == run["id"]
        assert trial["trial_number"] == 1
        assert trial["status"] == "completed"
        assert trial["is_best"] is False
        assert trial["params"]["buy"]["rsi"] == 30
        assert trial["profit_total"] == 100.0
        assert trial["trade_count"] == 50

    def test_bulk_create_trials(self, repo, sample_run_data):
        """Test creating multiple trials in bulk."""
        run = repo.create_optimization_run(sample_run_data)

        trials_data = []
        for i in range(5):
            trials_data.append(
                {
                    "optimization_run_id": run["id"],
                    "trial_number": i + 1,
                    "status": "completed",
                    "is_best": False,
                    "params": {"buy": {"rsi": 30 + i}, "sell": {"rsi": 70 - i}},
                    "profit_total": 100.0 + i * 10,
                    "trade_count": 50 + i * 5,
                }
            )

        trials = repo.bulk_create_trials(trials_data)

        assert len(trials) == 5
        assert all(t["optimization_run_id"] == run["id"] for t in trials)
        assert trials[0]["trial_number"] == 1
        assert trials[4]["trial_number"] == 5

    def test_get_trial(self, repo, sample_run_data, sample_trial_data):
        """Test getting a trial by ID."""
        run = repo.create_optimization_run(sample_run_data)
        sample_trial_data["optimization_run_id"] = run["id"]
        created = repo.create_trial(sample_trial_data)

        retrieved = repo.get_trial(created["id"])

        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["trial_number"] == created["trial_number"]

    def test_list_trials(self, repo, sample_run_data):
        """Test listing trials for an optimization run."""
        run = repo.create_optimization_run(sample_run_data)

        # Create multiple trials
        for i in range(3):
            repo.create_trial(
                {
                    "optimization_run_id": run["id"],
                    "trial_number": i + 1,
                    "status": "completed",
                    "is_best": False,
                    "params": {"buy": {"rsi": 30}},
                    "trade_count": 50,
                }
            )

        trials = repo.list_trials(run["id"])

        assert len(trials) == 3
        assert all(t["optimization_run_id"] == run["id"] for t in trials)
        assert trials[0]["trial_number"] == 1
        assert trials[2]["trial_number"] == 3

    def test_list_trials_with_status_filter(self, repo, sample_run_data):
        """Test listing trials with status filter."""
        run = repo.create_optimization_run(sample_run_data)

        repo.create_trial(
            {
                "optimization_run_id": run["id"],
                "trial_number": 1,
                "status": "completed",
                "is_best": False,
                "params": {},
                "trade_count": 50,
            }
        )
        repo.create_trial(
            {
                "optimization_run_id": run["id"],
                "trial_number": 2,
                "status": "failed",
                "is_best": False,
                "params": {},
                "trade_count": 0,
                "failure_reason": "No trades",
            }
        )

        completed_trials = repo.list_trials(run["id"], status="completed")
        failed_trials = repo.list_trials(run["id"], status="failed")

        assert len(completed_trials) == 1
        assert completed_trials[0]["status"] == "completed"
        assert len(failed_trials) == 1
        assert failed_trials[0]["status"] == "failed"
        assert failed_trials[0]["failure_reason"] == "No trades"

    def test_get_best_trial(self, repo, sample_run_data, sample_trial_data):
        """Test getting the best trial."""
        run = repo.create_optimization_run(sample_run_data)
        sample_trial_data["optimization_run_id"] = run["id"]
        sample_trial_data["is_best"] = True
        repo.create_trial(sample_trial_data)

        best_trial = repo.get_best_trial(run["id"])

        assert best_trial is not None
        assert best_trial["is_best"] is True
        assert best_trial["trial_number"] == 1

    def test_mark_best_trial(self, repo, sample_run_data):
        """Test marking a trial as best."""
        run = repo.create_optimization_run(sample_run_data)

        # Create multiple trials
        trial1 = repo.create_trial(
            {
                "optimization_run_id": run["id"],
                "trial_number": 1,
                "status": "completed",
                "is_best": True,
                "params": {},
                "trade_count": 50,
            }
        )
        trial2 = repo.create_trial(
            {
                "optimization_run_id": run["id"],
                "trial_number": 2,
                "status": "completed",
                "is_best": False,
                "params": {},
                "trade_count": 60,
            }
        )

        # Mark trial2 as best
        updated = repo.mark_best_trial(trial2["id"])

        assert updated is not None
        assert updated["is_best"] is True

        # Verify trial1 is no longer best
        trial1_retrieved = repo.get_trial(trial1["id"])
        assert trial1_retrieved["is_best"] is False

    def test_save_comparison(self, repo, sample_run_data):
        """Test saving comparison data."""
        run = repo.create_optimization_run(sample_run_data)

        comparison_data = {
            "baseline_metrics": {"profit_total": 100.0},
            "optimized_metrics": {"profit_total": 150.0},
            "metric_deltas": {"profit_total": 50.0},
            "recommendation": "improved",
        }

        updated = repo.save_comparison(run["id"], comparison_data)

        assert updated is not None
        assert updated["comparison"] is not None
        assert updated["comparison"]["recommendation"] == "improved"

    def test_get_comparison(self, repo, sample_run_data):
        """Test getting comparison data."""
        run = repo.create_optimization_run(sample_run_data)

        comparison_data = {"recommendation": "improved"}
        repo.save_comparison(run["id"], comparison_data)

        retrieved = repo.get_comparison(run["id"])

        assert retrieved is not None
        assert retrieved["recommendation"] == "improved"

    def test_serialize_run(self, repo, sample_run_data):
        """Test run serialization."""
        serialized = repo.serialize_run(sample_run_data)

        assert serialized is not None
        assert serialized["strategy_name"] == "TestStrategy"
        assert serialized["status"] == "pending"

    def test_serialize_trial(self, repo, sample_trial_data):
        """Test trial serialization."""
        serialized = repo.serialize_trial(sample_trial_data)

        assert serialized is not None
        assert serialized["trial_number"] == 1
        assert serialized["status"] == "completed"

    def test_all_params_json_round_trip(self, repo, sample_run_data):
        """Test that all parameter JSON fields round-trip correctly."""
        run = repo.create_optimization_run(sample_run_data)

        complex_params = {
            "buy": {"rsi": 30, "bb": {"lower": 20, "upper": 80}},
            "sell": {"rsi": 70, "macd": {"signal": 0.5}},
            "roi": {"0": 0.05, "1": 0.10, "2": 0.15},
            "stoploss": {"value": -0.10},
        }

        trial = repo.create_trial(
            {
                "optimization_run_id": run["id"],
                "trial_number": 1,
                "status": "completed",
                "is_best": False,
                "params": complex_params,
                "buy_params": complex_params["buy"],
                "sell_params": complex_params["sell"],
                "roi_params": complex_params["roi"],
                "stoploss_params": complex_params["stoploss"],
                "trade_count": 50,
            }
        )

        retrieved = repo.get_trial(trial["id"])

        assert retrieved["params"]["buy"]["bb"]["lower"] == 20
        assert retrieved["params"]["sell"]["macd"]["signal"] == 0.5
        assert retrieved["roi_params"]["2"] == 0.15
        assert retrieved["stoploss_params"]["value"] == -0.10

    def test_rejected_failed_trial_persists_reason(self, repo, sample_run_data):
        """Test that rejected and failed trials persist their reasons."""
        run = repo.create_optimization_run(sample_run_data)

        rejected_trial = repo.create_trial(
            {
                "optimization_run_id": run["id"],
                "trial_number": 1,
                "status": "rejected",
                "is_best": False,
                "params": {},
                "rejection_reason": "Insufficient trades",
                "trade_count": 5,
            }
        )

        failed_trial = repo.create_trial(
            {
                "optimization_run_id": run["id"],
                "trial_number": 2,
                "status": "failed",
                "is_best": False,
                "params": {},
                "failure_reason": "Strategy error",
                "trade_count": 0,
            }
        )

        assert rejected_trial["rejection_reason"] == "Insufficient trades"
        assert failed_trial["failure_reason"] == "Strategy error"

    def test_every_trial_persists_not_just_best(self, repo, sample_run_data):
        """Test that every trial is persisted, not just the best trial."""
        run = repo.create_optimization_run(sample_run_data)

        # Create 10 trials, only one marked as best
        for i in range(10):
            repo.create_trial(
                {
                    "optimization_run_id": run["id"],
                    "trial_number": i + 1,
                    "status": "completed",
                    "is_best": (i == 5),  # Only trial 6 is best
                    "params": {"buy": {"rsi": 30 + i}},
                    "trade_count": 50 + i,
                }
            )

        all_trials = repo.list_trials(run["id"])

        assert len(all_trials) == 10
        assert sum(1 for t in all_trials if t["is_best"]) == 1
        assert all(t["trial_number"] == i + 1 for i, t in enumerate(all_trials))

    def test_invalid_status_raises_error(self, repo):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid optimization status"):
            repo._require_allowed("invalid_status", OPTIMIZATION_STATUSES, "optimization status")

    def test_invalid_trial_status_raises_error(self, repo):
        """Test that invalid trial status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid trial status"):
            repo._require_allowed("invalid_status", OPTIMIZATION_TRIAL_STATUSES, "trial status")

    def test_invalid_result_status_raises_error(self, repo):
        """Test that invalid result status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid optimization result status"):
            repo._require_allowed(
                "invalid_status", OPTIMIZATION_RESULT_STATUSES, "optimization result status"
            )
