#!/usr/bin/env python3
"""
Seed safe HER demo data for frontend/backend development.

Demo data is explicitly marked and must not be treated as real trading evidence.
"""
import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db.sqlite import initialize_database, transaction
from app.repositories.artifacts import ArtifactRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.logs import RunLogRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.run_stages import RunStageRepository
from app.repositories.runs import RunRepository
from app.repositories.strategies import StrategyRepository
from app.schemas.artifacts import ArtifactCreate
from app.schemas.audit_logs import AuditLogCreate
from app.schemas.metrics import MetricSnapshotCreate, PairResultCreate, TradeSummaryCreate
from app.schemas.runs import RunCreate
from app.schemas.strategies import StrategyCreate, StrategyVersionCreate


def clear_demo_data() -> dict[str, int]:
    """Delete demo records only."""
    deleted = {}
    with transaction() as conn:
        demo_run_ids = [
            row["id"]
            for row in conn.execute("SELECT id FROM runs WHERE is_demo = 1").fetchall()
        ]
        demo_strategy_ids = [
            row["id"]
            for row in conn.execute("SELECT id FROM strategies WHERE is_demo = 1").fetchall()
        ]

        for table in (
            "audit_logs",
            "retry_history",
            "run_logs",
            "trade_summaries",
            "pair_results",
            "metrics_snapshots",
            "artifacts",
            "run_stages",
        ):
            if demo_run_ids:
                placeholders = ",".join("?" for _ in demo_run_ids)
                cursor = conn.execute(
                    f"DELETE FROM {table} WHERE run_id IN ({placeholders})",
                    tuple(demo_run_ids),
                )
                deleted[table] = cursor.rowcount
            else:
                deleted[table] = 0

        if demo_run_ids:
            placeholders = ",".join("?" for _ in demo_run_ids)
            cursor = conn.execute(
                f"DELETE FROM runs WHERE id IN ({placeholders})",
                tuple(demo_run_ids),
            )
            deleted["runs"] = cursor.rowcount
        else:
            deleted["runs"] = 0

        if demo_strategy_ids:
            placeholders = ",".join("?" for _ in demo_strategy_ids)
            cursor = conn.execute(
                f"DELETE FROM strategy_versions WHERE strategy_id IN ({placeholders})",
                tuple(demo_strategy_ids),
            )
            deleted["strategy_versions"] = cursor.rowcount

            cursor = conn.execute(
                f"DELETE FROM artifacts WHERE strategy_id IN ({placeholders})",
                tuple(demo_strategy_ids),
            )
            deleted["strategy_artifacts"] = cursor.rowcount

            cursor = conn.execute(
                f"DELETE FROM strategies WHERE id IN ({placeholders})",
                tuple(demo_strategy_ids),
            )
            deleted["strategies"] = cursor.rowcount
        else:
            deleted["strategy_versions"] = 0
            deleted["strategy_artifacts"] = 0
            deleted["strategies"] = 0

    return deleted


def seed_demo_data() -> dict[str, str]:
    """Create one coherent demo strategy and demo run."""
    initialize_database()
    clear_demo_data()

    strategy_repo = StrategyRepository()
    run_repo = RunRepository()
    stage_repo = RunStageRepository()
    metrics_repo = MetricsRepository()
    artifact_repo = ArtifactRepository()
    log_repo = RunLogRepository()
    audit_repo = AuditLogRepository()

    strategy = strategy_repo.create_strategy(
        StrategyCreate(
            name="DemoMomentumStrategy",
            class_name="DemoMomentumStrategy",
            source_type="demo",
            timeframe="15m",
            direction="long",
            file_path="artifacts/demo/DemoMomentumStrategy.py",
            params_path="artifacts/demo/DemoMomentumStrategy.json",
            status="draft",
            is_demo=True,
        )
    )

    version = strategy_repo.create_version(
        StrategyVersionCreate(
            strategy_id=strategy["id"],
            version_number=1,
            py_path="artifacts/demo/DemoMomentumStrategy.py",
            json_path="artifacts/demo/DemoMomentumStrategy.json",
            spec={
                "demo": True,
                "name": "DemoMomentumStrategy",
                "description": "Demo placeholder only, not real trading logic",
                "timeframe": "15m",
                "indicators": ["ema", "rsi"],
            },
            params={
                "demo": True,
                "buy_rsi": 35,
                "sell_rsi": 70,
                "stoploss": -0.08,
            },
            notes="Demo placeholder only, not real trading logic",
        )
    )

    run = run_repo.create_run(
        RunCreate(
            name="Demo AutoQuant Run",
            mode="manual_test",
            strategy_id=strategy["id"],
            exchange="binance",
            quote_currency="USDT",
            trading_mode="spot",
            timeframe="15m",
            pairs=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            timerange="20240101-20240601",
            risk_profile="balanced",
            analysis_depth="standard",
            is_demo=True,
        )
    )
    run = run_repo.mark_completed(run["id"], status="validated", classification="validated")

    for stage_key in (
        "run_setup",
        "preflight_checks",
        "strategy_normalization",
        "pair_timeframe_selection",
        "data_availability",
        "baseline_backtest",
        "final_classification",
    ):
        stage_repo.complete_stage(
            run["id"],
            stage_key,
            output_data={"demo": True, "status": "passed"},
            logs_summary="Demo stage marked passed; no real pipeline execution.",
        )
    stage_repo.skip_stage(run["id"], "hyperopt", reason="Demo seed skips hyperopt.")

    log_repo.add_log(
        run_id=run["id"],
        level="warning",
        source="system",
        message="Demo data seeded; not real trading evidence.",
        stage_key="run_setup",
        details={"demo": True, "real_trading_result": False},
    )

    metrics_repo.create_metric_snapshot(
        MetricSnapshotCreate(
            run_id=run["id"],
            stage_key="baseline_backtest",
            net_profit=0.184,
            profit_factor=1.35,
            max_drawdown=12.1,
            sharpe=1.12,
            calmar=1.44,
            win_rate=54.2,
            trade_count=120,
            expectancy=0.42,
            avg_win=2.1,
            avg_loss=-1.3,
            raw_json={"demo": True, "source": "seed-demo-data.py"},
        )
    )

    for pair, profit, trades in (
        ("BTC/USDT", 0.092, 44),
        ("ETH/USDT", 0.061, 39),
        ("SOL/USDT", 0.031, 37),
    ):
        metrics_repo.create_pair_result(
            PairResultCreate(
                run_id=run["id"],
                pair=pair,
                net_profit=profit,
                profit_factor=1.35,
                max_drawdown=12.1,
                trade_count=trades,
                win_rate=54.0,
                expectancy=0.4,
                raw_json={"demo": True, "pair": pair},
            )
        )

    metrics_repo.create_trade_summary(
        TradeSummaryCreate(
            run_id=run["id"],
            total_trades=120,
            wins=65,
            losses=49,
            draws=6,
            avg_duration="3h 15m",
            best_pair="BTC/USDT",
            worst_pair="SOL/USDT",
            raw_json={"demo": True},
        )
    )

    for artifact_type, file_path, description in (
        ("strategy_py", "artifacts/demo/DemoMomentumStrategy.py", "Demo strategy placeholder path"),
        ("strategy_json", "artifacts/demo/DemoMomentumStrategy.json", "Demo params placeholder path"),
        ("metrics_json", "artifacts/demo/demo-metrics.json", "Demo metrics placeholder path"),
        ("backtest_raw", "artifacts/demo/demo-backtest-raw.json", "Demo raw backtest placeholder path"),
    ):
        artifact_repo.create_artifact(
            ArtifactCreate(
                run_id=run["id"],
                strategy_id=strategy["id"],
                artifact_type=artifact_type,
                file_path=file_path,
                description=description,
            )
        )

    audit_repo.create_audit_log(
        AuditLogCreate(
            run_id=run["id"],
            actor="system",
            action_type="seed_demo_data",
            description="Seeded safe demo data for Part 03 development",
            target_type="run",
            target_id=run["id"],
            after={"demo": True, "strategy_id": strategy["id"], "version_id": version["id"]},
            approved=True,
            notes="Demo data only; not real trading evidence.",
        )
    )

    return {
        "strategy_id": strategy["id"],
        "strategy_version_id": version["id"],
        "run_id": run["id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or clear HER demo data.")
    parser.add_argument("--clear", action="store_true", help="Clear demo data only.")
    args = parser.parse_args()

    initialize_database()
    if args.clear:
        deleted = clear_demo_data()
        print("Cleared demo data only:")
        for table, count in sorted(deleted.items()):
            print(f"  {table}: {count}")
        return

    created = seed_demo_data()
    print("Seeded HER demo data:")
    for key, value in created.items():
        print(f"  {key}: {value}")
    print("Demo data is marked is_demo=true and is not real trading evidence.")


if __name__ == "__main__":
    main()
