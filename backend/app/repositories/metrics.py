"""
Repository for Metrics operations.
"""
from typing import Optional, List

from app.db.sqlite import fetch_one, fetch_all, execute, transaction
from app.repositories.base import BaseRepository
from app.schemas.metrics import (
    MetricSnapshotCreate,
    PairResultCreate,
    TradeSummaryCreate,
)


class MetricsRepository(BaseRepository):
    """Repository for metrics, pair results, and trade summaries data access operations."""
    
    def create_metric_snapshot(self, data: MetricSnapshotCreate) -> dict:
        """
        Create a metric snapshot.
        
        Args:
            data: Metric snapshot creation data
        
        Returns:
            Created metric snapshot as dictionary
        """
        snapshot_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO metrics_snapshots (
                    id, run_id, stage_key, net_profit, profit_factor,
                    max_drawdown, sharpe, calmar, win_rate, trade_count,
                    expectancy, avg_win, avg_loss, raw_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    data.run_id,
                    data.stage_key,
                    data.net_profit,
                    data.profit_factor,
                    data.max_drawdown,
                    data.sharpe,
                    data.calmar,
                    data.win_rate,
                    data.trade_count,
                    data.expectancy,
                    data.avg_win,
                    data.avg_loss,
                    self._json_dumps(data.raw_json) if data.raw_json else None,
                    now,
                )
            )
        
        return self._deserialize_snapshot(self.get_metric_snapshot(snapshot_id))
    
    def get_metric_snapshot(self, snapshot_id: str) -> Optional[dict]:
        """
        Get a metric snapshot by ID.
        
        Args:
            snapshot_id: Snapshot UUID
        
        Returns:
            Snapshot as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM metrics_snapshots WHERE id = ?",
            (snapshot_id,)
        )
        
        if row:
            return self._row_to_dict(row)
        return None
    
    def list_metric_snapshots(self, run_id: str) -> List[dict]:
        """
        List all metric snapshots for a run.
        
        Args:
            run_id: Run UUID
        
        Returns:
            List of metric snapshot dictionaries
        """
        rows = fetch_all(
            "SELECT * FROM metrics_snapshots WHERE run_id = ? ORDER BY created_at DESC",
            (run_id,)
        )
        
        return [self._deserialize_snapshot(self._row_to_dict(row)) for row in rows]
    
    def get_latest_metric_snapshot(self, run_id: str) -> Optional[dict]:
        """
        Get the latest metric snapshot for a run.
        
        Args:
            run_id: Run UUID
        
        Returns:
            Latest snapshot as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM metrics_snapshots WHERE run_id = ? ORDER BY created_at DESC LIMIT 1",
            (run_id,)
        )
        
        if row:
            return self._deserialize_snapshot(self._row_to_dict(row))
        return None
    
    def create_pair_result(self, data: PairResultCreate) -> dict:
        """
        Create a pair result.
        
        Args:
            data: Pair result creation data
        
        Returns:
            Created pair result as dictionary
        """
        result_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO pair_results (
                    id, run_id, pair, net_profit, profit_factor, max_drawdown,
                    trade_count, win_rate, expectancy, raw_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    data.run_id,
                    data.pair,
                    data.net_profit,
                    data.profit_factor,
                    data.max_drawdown,
                    data.trade_count,
                    data.win_rate,
                    data.expectancy,
                    self._json_dumps(data.raw_json) if data.raw_json else None,
                    now,
                )
            )
        
        return self._deserialize_pair_result(self.get_pair_result(result_id))

    def upsert_pair_result(self, data: PairResultCreate) -> dict:
        """
        Insert or replace a pair result for a run/pair.

        The pair_results table has a UNIQUE(run_id, pair) constraint. This
        helper keeps parser re-runs idempotent without deleting raw artifacts.
        """
        existing = self.get_pair_result_by_run_pair(data.run_id, data.pair) if data.run_id else None
        result_id = existing["id"] if existing else self._uuid()
        now = self._now()

        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO pair_results (
                    id, run_id, pair, net_profit, profit_factor, max_drawdown,
                    trade_count, win_rate, expectancy, raw_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, pair) DO UPDATE SET
                    net_profit = excluded.net_profit,
                    profit_factor = excluded.profit_factor,
                    max_drawdown = excluded.max_drawdown,
                    trade_count = excluded.trade_count,
                    win_rate = excluded.win_rate,
                    expectancy = excluded.expectancy,
                    raw_json = excluded.raw_json,
                    created_at = excluded.created_at
                """,
                (
                    result_id,
                    data.run_id,
                    data.pair,
                    data.net_profit,
                    data.profit_factor,
                    data.max_drawdown,
                    data.trade_count,
                    data.win_rate,
                    data.expectancy,
                    self._json_dumps(data.raw_json) if data.raw_json else None,
                    now,
                )
            )

        return self._deserialize_pair_result(self.get_pair_result_by_run_pair(data.run_id, data.pair))
    
    def get_pair_result(self, result_id: str) -> Optional[dict]:
        """
        Get a pair result by ID.
        
        Args:
            result_id: Pair result UUID
        
        Returns:
            Pair result as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM pair_results WHERE id = ?",
            (result_id,)
        )
        
        if row:
            return self._row_to_dict(row)
        return None

    def get_pair_result_by_run_pair(self, run_id: str, pair: str) -> Optional[dict]:
        """Get a pair result by run ID and pair name."""
        row = fetch_one(
            "SELECT * FROM pair_results WHERE run_id = ? AND pair = ?",
            (run_id, pair)
        )

        if row:
            return self._deserialize_pair_result(self._row_to_dict(row))
        return None
    
    def list_pair_results(self, run_id: str) -> List[dict]:
        """
        List all pair results for a run.
        
        Args:
            run_id: Run UUID
        
        Returns:
            List of pair result dictionaries
        """
        rows = fetch_all(
            "SELECT * FROM pair_results WHERE run_id = ? ORDER BY pair ASC",
            (run_id,)
        )
        
        return [self._deserialize_pair_result(self._row_to_dict(row)) for row in rows]
    
    def create_trade_summary(self, data: TradeSummaryCreate) -> dict:
        """
        Create a trade summary.
        
        Args:
            data: Trade summary creation data
        
        Returns:
            Created trade summary as dictionary
        """
        summary_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO trade_summaries (
                    id, run_id, total_trades, wins, losses, draws,
                    avg_duration, best_pair, worst_pair, raw_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary_id,
                    data.run_id,
                    data.total_trades,
                    data.wins,
                    data.losses,
                    data.draws,
                    data.avg_duration,
                    data.best_pair,
                    data.worst_pair,
                    self._json_dumps(data.raw_json) if data.raw_json else None,
                    now,
                )
            )
        
        return self._deserialize_trade_summary(self.get_trade_summary_by_id(summary_id))

    def replace_trade_summary(self, data: TradeSummaryCreate) -> dict:
        """
        Replace the trade summary for a run.

        The table does not have a unique run_id constraint, so parser re-runs
        delete existing summary rows for the run before inserting the current
        parse result.
        """
        with transaction() as conn:
            conn.execute("DELETE FROM trade_summaries WHERE run_id = ?", (data.run_id,))

        return self.create_trade_summary(data)

    def delete_metric_snapshots(self, run_id: str) -> int:
        """Delete metric snapshots for a run and return deleted count."""
        with transaction() as conn:
            cursor = conn.execute("DELETE FROM metrics_snapshots WHERE run_id = ?", (run_id,))
            return cursor.rowcount
    
    def get_trade_summary_by_id(self, summary_id: str) -> Optional[dict]:
        """
        Get a trade summary by ID.
        
        Args:
            summary_id: Trade summary UUID
        
        Returns:
            Trade summary as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM trade_summaries WHERE id = ?",
            (summary_id,)
        )
        
        if row:
            return self._row_to_dict(row)
        return None
    
    def get_trade_summary(self, run_id: str) -> Optional[dict]:
        """
        Get the trade summary for a run.
        
        Args:
            run_id: Run UUID
        
        Returns:
            Trade summary as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM trade_summaries WHERE run_id = ?",
            (run_id,)
        )
        
        if row:
            return self._deserialize_trade_summary(self._row_to_dict(row))
        return None

    def get_trade_summary_by_run(self, run_id: str) -> Optional[dict]:
        """Backward-compatible alias for run-based trade summary lookup."""
        return self.get_trade_summary(run_id)
    
    def _deserialize_snapshot(self, row: dict) -> dict:
        """Deserialize a metric snapshot row, converting JSON field to object."""
        if row.get("raw_json"):
            row["raw_json"] = self._json_loads(row["raw_json"])
        return row
    
    def _deserialize_pair_result(self, row: dict) -> dict:
        """Deserialize a pair result row, converting JSON field to object."""
        if row.get("raw_json"):
            row["raw_json"] = self._json_loads(row["raw_json"])
        return row
    
    def _deserialize_trade_summary(self, row: dict) -> dict:
        """Deserialize a trade summary row, converting JSON field to object."""
        if row.get("raw_json"):
            row["raw_json"] = self._json_loads(row["raw_json"])
        return row
