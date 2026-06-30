#!/usr/bin/env python3
"""
CLI entry point for Part 08 optimization pipeline real validation.
Calls OptimizationPipelineService and prints final markers.

This script provides a safe command-line way to run the complete Part 08
optimization pipeline and validate it with real Freqtrade Hyperopt.

IMPORTANT:
- This script does NOT call Ollama
- This script does NOT send Discord messages
- This script does NOT approve/export strategies
- This script does NOT guarantee profitability
- This script is for validation and testing purposes only
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.schemas.optimization import OptimizationRequest
from app.services.optimization_pipeline_service import OptimizationPipelineService
from app.repositories.optimization import OptimizationRepository
from app.repositories.runs import RunRepository
from app.services.hyperopt_policy_service import HyperoptPolicyService
from app.services.freqtrade_hyperopt_runner import FreqtradeHyperoptRunner
from app.services.hyperopt_result_parser import HyperoptResultParser
from app.services.optimized_backtest_service import OptimizedBacktestService
from app.services.strategy_params_materializer import StrategyParamsMaterializer
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run HER optimization pipeline",
        epilog="This script runs the complete Part 08 optimization pipeline with real Freqtrade Hyperopt."
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Strategy name to optimize"
    )
    parser.add_argument(
        "--pair",
        action="append",
        dest="pairs_list",
        help="Trading pair (repeatable, e.g., --pair BTC/USDT --pair ETH/USDT)"
    )
    parser.add_argument(
        "--pairs",
        help="Comma-separated trading pairs (alternative to --pair, e.g., BTC/USDT,ETH/USDT)"
    )
    parser.add_argument(
        "--timeframe",
        required=True,
        help="Timeframe (e.g., 1h, 4h, 1d)"
    )
    parser.add_argument(
        "--exchange",
        default="binance",
        help="Exchange (default: binance)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of data (default: 30)"
    )
    parser.add_argument(
        "--timerange",
        help="Specific time range (optional)"
    )
    parser.add_argument(
        "--risk-profile",
        default="balanced",
        choices=["conservative", "balanced", "aggressive"],
        help="Risk profile (default: balanced)"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of hyperopt epochs (default: 50)"
    )
    parser.add_argument(
        "--spaces",
        default="buy,sell",
        help="Comma-separated hyperopt spaces (default: buy,sell)"
    )
    parser.add_argument(
        "--download-missing-data",
        action="store_true",
        help="Download missing market data (requires --user-confirmed)"
    )
    parser.add_argument(
        "--user-confirmed",
        action="store_true",
        help="Confirm resource-intensive operations (Hyperopt, backtest, data download)"
    )
    parser.add_argument(
        "--apply-decision-to-run",
        action="store_true",
        default=True,
        help="Apply decision classification to run (default: True)"
    )
    parser.add_argument(
        "--baseline-run-id",
        help="Optional existing baseline run ID to reuse"
    )
    parser.add_argument(
        "--run-baseline-first",
        action="store_true",
        default=True,
        help="Run baseline before optimization (default: True)"
    )

    args = parser.parse_args()

    # Handle pairs from either --pair (repeatable) or --pairs (comma-separated)
    pairs = []
    if args.pairs_list:
        pairs.extend(args.pairs_list)
    if args.pairs:
        # If --pairs was used, split by comma
        pairs.extend([p.strip() for p in args.pairs.split(",")])
    
    if not pairs:
        parser.error("At least one pair must be specified via --pair or --pairs")

    # Parse spaces
    spaces = [s.strip() for s in args.spaces.split(",")]

    print("=" * 80)
    print("HER OPTIMIZATION PIPELINE - REAL VALIDATION")
    print("=" * 80)
    print(f"Strategy: {args.strategy}")
    print(f"Pairs: {', '.join(pairs)}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Exchange: {args.exchange}")
    print(f"Days: {args.days}")
    if args.timerange:
        print(f"Timerange: {args.timerange}")
    print(f"Risk Profile: {args.risk_profile}")
    print(f"Epochs: {args.epochs}")
    print(f"Spaces: {', '.join(spaces)}")
    print(f"Download Missing Data: {args.download_missing_data}")
    print(f"User Confirmed: {args.user_confirmed}")
    print(f"Apply Decision to Run: {args.apply_decision_to_run}")
    if args.baseline_run_id:
        print(f"Baseline Run ID: {args.baseline_run_id}")
    print(f"Run Baseline First: {args.run_baseline_first}")
    print("=" * 80)
    print()

    # Build optimization request
    request = OptimizationRequest(
        strategy_name=args.strategy,
        pairs=pairs,
        timeframe=args.timeframe,
        exchange=args.exchange,
        days=args.days,
        timerange=args.timerange,
        risk_profile=args.risk_profile,
        baseline_run_id=args.baseline_run_id,
        run_baseline_first=args.run_baseline_first,
        download_missing_data=args.download_missing_data,
        user_confirmed=args.user_confirmed,
        epochs=args.epochs,
        spaces=spaces,
        apply_decision_to_run=args.apply_decision_to_run,
    )

    # Initialize pipeline service with dependencies
    optimization_repo = OptimizationRepository()
    run_repo = RunRepository()
    hyperopt_policy_service = HyperoptPolicyService()
    hyperopt_runner = FreqtradeHyperoptRunner()
    hyperopt_parser = HyperoptResultParser()
    optimized_backtest_service = OptimizedBacktestService()
    params_materializer = StrategyParamsMaterializer()
    config_generator = FreqtradeConfigGenerator()

    pipeline_service = OptimizationPipelineService(
        optimization_repo=optimization_repo,
        run_repo=run_repo,
        hyperopt_policy_service=hyperopt_policy_service,
        hyperopt_runner=hyperopt_runner,
        hyperopt_parser=hyperopt_parser,
        optimized_backtest_service=optimized_backtest_service,
        params_materializer=params_materializer,
        config_generator=config_generator,
    )

    # Run optimization pipeline
    print("Starting optimization pipeline...")
    print()

    result = pipeline_service.run_optimization(request)

    print()
    print("=" * 80)
    print("OPTIMIZATION PIPELINE RESULTS")
    print("=" * 80)
    print(f"optimization_run_id: {result.get('optimization_run_id', 'N/A')}")
    print(f"baseline_run_id: {result.get('baseline_run_id', 'N/A')}")
    print(f"optimized_run_id: {result.get('optimized_run_id', 'N/A')}")
    print(f"strategy_name: {result.get('strategy_name', args.strategy)}")
    print(f"pairs: {', '.join(pairs)}")
    print(f"timeframe: {args.timeframe}")
    print(f"status: {result.get('status', 'N/A')}")
    print(f"result_status: {result.get('result_status', 'N/A')}")
    print(f"trials_count: {result.get('trials_count', 0)}")
    print(f"best_trial_id: {result.get('best_trial_id', 'N/A')}")
    print(f"best_trial_number: {result.get('best_trial_number', 'N/A')}")
    print(f"optimized_classification: {result.get('optimized_classification', 'N/A')}")
    
    comparison = result.get('comparison', {})
    if comparison:
        print("baseline_metrics:")
        baseline_metrics = comparison.get('baseline_metrics', {})
        for key, value in baseline_metrics.items():
            print(f"  {key}: {value}")
        print("optimized_metrics:")
        optimized_metrics = comparison.get('optimized_metrics', {})
        for key, value in optimized_metrics.items():
            print(f"  {key}: {value}")
        print("comparison summary:")
        print(f"  delta_profit_factor: {comparison.get('delta_profit_factor', 'N/A')}")
        print(f"  delta_expectancy: {comparison.get('delta_expectancy', 'N/A')}")
        print(f"  delta_drawdown: {comparison.get('delta_drawdown', 'N/A')}")
        print(f"  delta_trade_count: {comparison.get('delta_trade_count', 'N/A')}")
        print(f"  improvement_summary: {comparison.get('improvement_summary', 'N/A')}")
    
    report_path = result.get('report_artifact_path', 'N/A')
    print(f"report_path: {report_path}")
    
    print()
    print("API endpoints to inspect later:")
    optimization_run_id = result.get('optimization_run_id', '{run_id}')
    print(f"  GET /api/optimization/runs/{optimization_run_id}")
    print(f"  GET /api/optimization/runs/{optimization_run_id}/status")
    print(f"  GET /api/optimization/runs/{optimization_run_id}/trials")
    print(f"  GET /api/optimization/runs/{optimization_run_id}/best-trial")
    print(f"  GET /api/optimization/runs/{optimization_run_id}/comparison")
    print(f"  GET /api/optimization/runs/{optimization_run_id}/report")
    
    warnings = result.get('warnings', [])
    if warnings:
        print()
        print("warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    errors = result.get('errors', [])
    if errors:
        print()
        print("errors:")
        for error in errors:
            print(f"  - {error}")
    
    print("=" * 80)
    print()

    # Print final markers
    status = result.get('status')
    
    if status == 'completed':
        print("REAL_OPTIMIZATION_PIPELINE_PASSED")
        sys.exit(0)
    elif status == 'failed_controlled':
        print("REAL_OPTIMIZATION_PIPELINE_FAILED_CONTROLLED")
        sys.exit(1)
    elif status == 'confirmation_required':
        print("REAL_OPTIMIZATION_PIPELINE_CONFIRMATION_REQUIRED")
        sys.exit(2)
    else:
        print(f"REAL_OPTIMIZATION_PIPELINE_UNKNOWN_STATUS: {status}")
        sys.exit(3)


if __name__ == "__main__":
    main()
