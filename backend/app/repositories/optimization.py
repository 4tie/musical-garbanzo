"""
Repository for Part 08 optimization run and trial persistence.
"""
from typing import Any, Dict, List, Optional

from app.core.constants import (
    OPTIMIZATION_STATUSES,
    OPTIMIZATION_RESULT_STATUSES,
    OPTIMIZATION_TRIAL_STATUSES,
)
from app.db.sqlite import fetch_all, fetch_one, transaction
from app.repositories.base import BaseRepository


class OptimizationRepository(BaseRepository):
    """Repository for optimization_runs and optimization_trials tables."""

    def create_optimization_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an optimization run.

        Args:
            run_data: Dictionary with optimization run data

        Returns:
            Created optimization run as dictionary
        """
        run_id = run_data.get("id") or self._uuid()
        created_at = run_data.get("created_at") or self._now()
        updated_at = run_data.get("updated_at") or self._now()

        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO optimization_runs (
                    id, parent_run_id, baseline_run_id, optimized_run_id,
                    strategy_name, timeframe, pairs_json, exchange, risk_profile,
                    status, result_status, best_trial_id, epochs_requested,
                    epochs_completed, spaces_json, policy_json, request_json,
                    comparison_json, report_artifact_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_data.get("parent_run_id"),
                    run_data.get("baseline_run_id"),
                    run_data.get("optimized_run_id"),
                    run_data["strategy_name"],
                    run_data["timeframe"],
                    self._json_dumps(run_data.get("pairs", [])),
                    run_data.get("exchange", "binance"),
                    run_data.get("risk_profile"),
                    run_data.get("status", "pending"),
                    run_data.get("result_status"),
                    run_data.get("best_trial_id"),
                    run_data.get("epochs_requested"),
                    run_data.get("epochs_completed"),
                    self._json_dumps(run_data.get("spaces")),
                    self._json_dumps(run_data.get("policy")),
                    self._json_dumps(run_data.get("request")),
                    self._json_dumps(run_data.get("comparison")),
                    run_data.get("report_artifact_path"),
                    created_at,
                    updated_at,
                ),
            )

        return self.get_optimization_run(run_id)

    def update_optimization_run(self, run_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an optimization run.

        Args:
            run_id: Optimization run ID
            updates: Dictionary of fields to update

        Returns:
            Updated optimization run as dictionary, or None if not found
        """
        if not updates:
            return self.get_optimization_run(run_id)

        # Build dynamic update query
        update_fields = []
        values = []
        for field, value in updates.items():
            if field in [
                "parent_run_id",
                "baseline_run_id",
                "optimized_run_id",
                "strategy_name",
                "timeframe",
                "exchange",
                "risk_profile",
                "status",
                "result_status",
                "best_trial_id",
                "epochs_requested",
                "epochs_completed",
                "report_artifact_path",
            ]:
                update_fields.append(f"{field} = ?")
                values.append(value)
            elif field in ["pairs", "spaces", "policy", "request", "comparison"]:
                json_field = f"{field}_json" if field != "pairs" else "pairs_json"
                update_fields.append(f"{json_field} = ?")
                values.append(self._json_dumps(value))

        if not update_fields:
            return self.get_optimization_run(run_id)

        # Always update updated_at
        update_fields.append("updated_at = ?")
        values.append(self._now())
        values.append(run_id)

        with transaction() as conn:
            conn.execute(
                f"UPDATE optimization_runs SET {', '.join(update_fields)} WHERE id = ?",
                values,
            )

        return self.get_optimization_run(run_id)

    def get_optimization_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an optimization run by ID.

        Args:
            run_id: Optimization run ID

        Returns:
            Optimization run as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM optimization_runs WHERE id = ?",
            (run_id,),
        )
        return self.deserialize_run(row) if row else None

    def list_optimization_runs(
        self,
        strategy_name: Optional[str] = None,
        status: Optional[str] = None,
        result_status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List optimization runs with optional filters.

        Args:
            strategy_name: Filter by strategy name
            status: Filter by status
            result_status: Filter by result status
            limit: Maximum number of runs to return

        Returns:
            List of optimization runs as dictionaries
        """
        normalized_limit = self._normalize_limit(limit, default=50, max_value=200)

        conditions = []
        params = []

        if strategy_name:
            conditions.append("strategy_name = ?")
            params.append(strategy_name)

        if status:
            self._require_allowed(status, OPTIMIZATION_STATUSES, "optimization status")
            conditions.append("status = ?")
            params.append(status)

        if result_status:
            self._require_allowed(
                result_status, OPTIMIZATION_RESULT_STATUSES, "optimization result status"
            )
            conditions.append("result_status = ?")
            params.append(result_status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(normalized_limit)

        rows = fetch_all(
            f"""
            SELECT * FROM optimization_runs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            tuple(params),
        )

        return [self.deserialize_run(row) for row in rows]

    def create_trial(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single optimization trial.

        Args:
            trial_data: Dictionary with trial data

        Returns:
            Created trial as dictionary
        """
        trial_id = trial_data.get("id") or self._uuid()
        created_at = trial_data.get("created_at") or self._now()

        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO optimization_trials (
                    id, optimization_run_id, trial_number, status, is_best,
                    is_selected_for_validation, params_json, buy_params_json,
                    sell_params_json, roi_params_json, stoploss_params_json,
                    trailing_params_json, metrics_json, loss_score, profit_total,
                    profit_factor, expectancy, max_drawdown, trade_count, win_rate,
                    rejection_reason, failure_reason, artifact_paths_json,
                    raw_trial_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trial_id,
                    trial_data["optimization_run_id"],
                    trial_data["trial_number"],
                    trial_data["status"],
                    1 if trial_data.get("is_best") else 0,
                    1 if trial_data.get("is_selected_for_validation") else 0,
                    self._json_dumps(trial_data.get("params", {})),
                    self._json_dumps(trial_data.get("buy_params")),
                    self._json_dumps(trial_data.get("sell_params")),
                    self._json_dumps(trial_data.get("roi_params")),
                    self._json_dumps(trial_data.get("stoploss_params")),
                    self._json_dumps(trial_data.get("trailing_params")),
                    self._json_dumps(trial_data.get("metrics")),
                    trial_data.get("loss_score"),
                    trial_data.get("profit_total"),
                    trial_data.get("profit_factor"),
                    trial_data.get("expectancy"),
                    trial_data.get("max_drawdown"),
                    trial_data.get("trade_count"),
                    trial_data.get("win_rate"),
                    trial_data.get("rejection_reason"),
                    trial_data.get("failure_reason"),
                    self._json_dumps(trial_data.get("artifact_paths", [])),
                    self._json_dumps(trial_data.get("raw_trial")),
                    created_at,
                ),
            )

        return self.get_trial(trial_id)

    def bulk_create_trials(self, trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple optimization trials in a single transaction.

        Args:
            trials: List of trial data dictionaries

        Returns:
            List of created trials as dictionaries
        """
        trial_ids = []

        with transaction() as conn:
            for trial_data in trials:
                trial_id = trial_data.get("id") or self._uuid()
                created_at = trial_data.get("created_at") or self._now()

                conn.execute(
                    """
                    INSERT INTO optimization_trials (
                        id, optimization_run_id, trial_number, status, is_best,
                        is_selected_for_validation, params_json, buy_params_json,
                        sell_params_json, roi_params_json, stoploss_params_json,
                        trailing_params_json, metrics_json, loss_score, profit_total,
                        profit_factor, expectancy, max_drawdown, trade_count, win_rate,
                        rejection_reason, failure_reason, artifact_paths_json,
                        raw_trial_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trial_id,
                        trial_data["optimization_run_id"],
                        trial_data["trial_number"],
                        trial_data["status"],
                        1 if trial_data.get("is_best") else 0,
                        1 if trial_data.get("is_selected_for_validation") else 0,
                        self._json_dumps(trial_data.get("params", {})),
                        self._json_dumps(trial_data.get("buy_params")),
                        self._json_dumps(trial_data.get("sell_params")),
                        self._json_dumps(trial_data.get("roi_params")),
                        self._json_dumps(trial_data.get("stoploss_params")),
                        self._json_dumps(trial_data.get("trailing_params")),
                        self._json_dumps(trial_data.get("metrics")),
                        trial_data.get("loss_score"),
                        trial_data.get("profit_total"),
                        trial_data.get("profit_factor"),
                        trial_data.get("expectancy"),
                        trial_data.get("max_drawdown"),
                        trial_data.get("trade_count"),
                        trial_data.get("win_rate"),
                        trial_data.get("rejection_reason"),
                        trial_data.get("failure_reason"),
                        self._json_dumps(trial_data.get("artifact_paths", [])),
                        self._json_dumps(trial_data.get("raw_trial")),
                        created_at,
                    ),
                )

                trial_ids.append(trial_id)

        # Fetch trials after transaction commits
        return [self.get_trial(trial_id) for trial_id in trial_ids]

    def get_trial(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a trial by ID.

        Args:
            trial_id: Trial ID

        Returns:
            Trial as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM optimization_trials WHERE id = ?",
            (trial_id,),
        )
        return self.deserialize_trial(row) if row else None

    def list_trials(
        self,
        optimization_run_id: str,
        status: Optional[str] = None,
        is_best: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List trials for an optimization run with optional filters.

        Args:
            optimization_run_id: Optimization run ID
            status: Filter by trial status
            is_best: Filter by is_best flag
            limit: Maximum number of trials to return

        Returns:
            List of trials as dictionaries
        """
        normalized_limit = self._normalize_limit(limit, default=100, max_value=500)

        conditions = ["optimization_run_id = ?"]
        params = [optimization_run_id]

        if status:
            self._require_allowed(status, OPTIMIZATION_TRIAL_STATUSES, "trial status")
            conditions.append("status = ?")
            params.append(status)

        if is_best is not None:
            conditions.append("is_best = ?")
            params.append(1 if is_best else 0)

        where_clause = " AND ".join(conditions)
        params.append(normalized_limit)

        rows = fetch_all(
            f"""
            SELECT * FROM optimization_trials
            WHERE {where_clause}
            ORDER BY trial_number ASC
            LIMIT ?
            """,
            tuple(params),
        )

        return [self.deserialize_trial(row) for row in rows]

    def get_best_trial(self, optimization_run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the best trial for an optimization run.

        Args:
            optimization_run_id: Optimization run ID

        Returns:
            Best trial as dictionary, or None if not found
        """
        row = fetch_one(
            """
            SELECT * FROM optimization_trials
            WHERE optimization_run_id = ? AND is_best = 1
            LIMIT 1
            """,
            (optimization_run_id,),
        )
        return self.deserialize_trial(row) if row else None

    def mark_best_trial(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """
        Mark a trial as the best trial for its optimization run.

        This clears the is_best flag from all other trials in the same run.

        Args:
            trial_id: Trial ID to mark as best

        Returns:
            Updated trial as dictionary, or None if not found
        """
        trial = self.get_trial(trial_id)
        if not trial:
            return None

        optimization_run_id = trial["optimization_run_id"]

        with transaction() as conn:
            # Clear is_best from all trials in the run
            conn.execute(
                "UPDATE optimization_trials SET is_best = 0 WHERE optimization_run_id = ?",
                (optimization_run_id,),
            )

            # Set is_best on the specified trial
            conn.execute(
                "UPDATE optimization_trials SET is_best = 1 WHERE id = ?",
                (trial_id,),
            )

        return self.get_trial(trial_id)

    def save_comparison(
        self, optimization_run_id: str, comparison_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Save comparison data to an optimization run.

        Args:
            optimization_run_id: Optimization run ID
            comparison_data: Comparison data dictionary

        Returns:
            Updated optimization run as dictionary, or None if not found
        """
        return self.update_optimization_run(
            optimization_run_id, {"comparison": comparison_data}
        )

    def get_comparison(self, optimization_run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comparison data for an optimization run.

        Args:
            optimization_run_id: Optimization run ID

        Returns:
            Comparison data as dictionary, or None if not found
        """
        run = self.get_optimization_run(optimization_run_id)
        return run.get("comparison") if run else None

    def serialize_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert optimization run data to persistence format.

        Args:
            run_data: Raw run data

        Returns:
            Serialized run data for database
        """
        serialized = dict(run_data)

        # Validate status
        if "status" in serialized:
            self._require_allowed(
                serialized["status"], OPTIMIZATION_STATUSES, "optimization status"
            )

        # Validate result_status
        if "result_status" in serialized:
            self._require_allowed(
                serialized["result_status"],
                OPTIMIZATION_RESULT_STATUSES,
                "optimization result status",
            )

        return self._sanitize_secret_like(serialized)

    def serialize_trial(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert trial data to persistence format.

        Args:
            trial_data: Raw trial data

        Returns:
            Serialized trial data for database
        """
        serialized = dict(trial_data)

        # Validate status
        if "status" in serialized:
            self._require_allowed(
                serialized["status"], OPTIMIZATION_TRIAL_STATUSES, "trial status"
            )

        return self._sanitize_secret_like(serialized)

    def deserialize_run(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserialize an optimization_runs row into API-friendly dictionary.

        Args:
            row: Database row

        Returns:
            Deserialized run data
        """
        if not row:
            return None

        run = {
            "id": row["id"],
            "parent_run_id": row.get("parent_run_id"),
            "baseline_run_id": row.get("baseline_run_id"),
            "optimized_run_id": row.get("optimized_run_id"),
            "strategy_name": row["strategy_name"],
            "timeframe": row["timeframe"],
            "pairs": self._json_loads(row.get("pairs_json"), default=[]),
            "exchange": row.get("exchange"),
            "risk_profile": row.get("risk_profile"),
            "status": row["status"],
            "result_status": row.get("result_status"),
            "best_trial_id": row.get("best_trial_id"),
            "epochs_requested": row.get("epochs_requested"),
            "epochs_completed": row.get("epochs_completed"),
            "spaces": self._json_loads(row.get("spaces_json")),
            "policy": self._json_loads(row.get("policy_json")),
            "request": self._json_loads(row.get("request_json")),
            "comparison": self._json_loads(row.get("comparison_json")),
            "report_artifact_path": row.get("report_artifact_path"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

        return run

    def deserialize_trial(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserialize an optimization_trials row into API-friendly dictionary.

        Args:
            row: Database row

        Returns:
            Deserialized trial data
        """
        if not row:
            return None

        trial = {
            "id": row["id"],
            "optimization_run_id": row["optimization_run_id"],
            "trial_number": row["trial_number"],
            "status": row["status"],
            "is_best": bool(row.get("is_best", 0)),
            "is_selected_for_validation": bool(row.get("is_selected_for_validation", 0)),
            "params": self._json_loads(row.get("params_json"), default={}),
            "buy_params": self._json_loads(row.get("buy_params_json")),
            "sell_params": self._json_loads(row.get("sell_params_json")),
            "roi_params": self._json_loads(row.get("roi_params_json")),
            "stoploss_params": self._json_loads(row.get("stoploss_params_json")),
            "trailing_params": self._json_loads(row.get("trailing_params_json")),
            "metrics": self._json_loads(row.get("metrics_json")),
            "loss_score": row.get("loss_score"),
            "profit_total": row.get("profit_total"),
            "profit_factor": row.get("profit_factor"),
            "expectancy": row.get("expectancy"),
            "max_drawdown": row.get("max_drawdown"),
            "trade_count": row.get("trade_count"),
            "win_rate": row.get("win_rate"),
            "rejection_reason": row.get("rejection_reason"),
            "failure_reason": row.get("failure_reason"),
            "artifact_paths": self._json_loads(row.get("artifact_paths_json"), default=[]),
            "raw_trial": self._json_loads(row.get("raw_trial_json")),
            "created_at": row["created_at"],
        }

        return trial
