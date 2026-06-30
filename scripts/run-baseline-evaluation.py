#!/usr/bin/env python3
"""
CLI script for real baseline evaluation of existing Freqtrade strategies.

This script provides a safe command-line way to run the complete Part 07 baseline
pipeline with a real strategy, real data, real backtest, real parser, and real decision.

Safety rules:
- Does not call Ollama
- Does not send Discord messages
- Does not approve/export strategies
- Does not start live trading
- Does not create fake evidence
- Only runs real Freqtrade backtesting through BaselineEvaluationService
- Only runs backtest when --user-confirmed is present
"""
import argparse
import sys
from pathlib import Path

# Add project root and backend to path
project_root = Path(__file__).parent.parent
backend_root = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_root))

from app.schemas.baseline import BaselineEvaluationRequest
from app.services.baseline_evaluation_service import BaselineEvaluationService


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run real baseline evaluation for an existing Freqtrade strategy"
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Existing Freqtrade strategy name"
    )
    parser.add_argument(
        "--pair",
        action="append",
        dest="pairs",
        help="Trading pair (can be repeated)"
    )
    parser.add_argument(
        "--pairs",
        help="Comma-separated list of trading pairs"
    )
    parser.add_argument(
        "--timeframe",
        required=True,
        help="Freqtrade timeframe (e.g., 5m, 1h, 4h)"
    )
    parser.add_argument(
        "--exchange",
        default="binance",
        help="Exchange name (default: binance)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Historical days to evaluate (default: 30)"
    )
    parser.add_argument(
        "--timerange",
        help="Optional Freqtrade timerange (e.g., 20240101-20241231)"
    )
    parser.add_argument(
        "--risk-profile",
        default="balanced",
        choices=["conservative", "balanced", "aggressive"],
        help="Decision risk profile (default: balanced)"
    )
    parser.add_argument(
        "--stake-currency",
        default="USDT",
        help="Stake currency (default: USDT)"
    )
    parser.add_argument(
        "--stake-amount",
        default="unlimited",
        help="Stake amount (default: unlimited)"
    )
    parser.add_argument(
        "--max-open-trades",
        type=int,
        default=3,
        help="Maximum open trades (default: 3)"
    )
    parser.add_argument(
        "--download-missing-data",
        action="store_true",
        help="Allow downloading missing market data (requires --user-confirmed)"
    )
    parser.add_argument(
        "--user-confirmed",
        action="store_true",
        help="User has confirmed real execution (required for backtest and data download)"
    )
    parser.add_argument(
        "--apply-decision-to-run",
        action="store_true",
        default=True,
        help="Apply decision classification to run (default: True)"
    )
    parser.add_argument(
        "--notes",
        help="Optional user notes"
    )
    return parser.parse_args()


def build_request(args):
    """Build BaselineEvaluationRequest from CLI arguments."""
    # Handle pairs from both --pair and --pairs
    pairs = []
    if args.pairs:
        pairs.extend(args.pairs)
    
    if not pairs:
        raise ValueError("At least one trading pair must be specified via --pair")
    
    return BaselineEvaluationRequest(
        strategy_name=args.strategy,
        pairs=pairs,
        timeframe=args.timeframe,
        exchange=args.exchange,
        days=args.days,
        timerange=args.timerange,
        risk_profile=args.risk_profile,
        stake_currency=args.stake_currency,
        stake_amount=args.stake_amount,
        max_open_trades=args.max_open_trades,
        trading_mode="spot",
        download_missing_data=args.download_missing_data,
        user_confirmed=args.user_confirmed,
        apply_decision_to_run=args.apply_decision_to_run,
        force_parse=True,
        notes=args.notes,
    )


def print_result(result):
    """Print evaluation result in a structured format."""
    print("\n" + "=" * 80)
    print("BASELINE EVALUATION RESULT")
    print("=" * 80)
    print(f"Run ID: {result.run_id}")
    print(f"Strategy: {result.strategy_name}")
    print(f"Pairs: {', '.join(result.pairs)}")
    print(f"Timeframe: {result.timeframe}")
    print(f"Exchange: {result.exchange}")
    print(f"Risk Profile: {result.risk_profile}")
    print(f"Status: {result.status}")
    print(f"Classification: {result.classification}")
    print(f"Confidence Score: {result.confidence_score}")
    
    # Print key metrics if available
    if result.metrics:
        print("\nKey Metrics:")
        print(f"  Trade Count: {result.metrics.get('trade_count', 'N/A')}")
        print(f"  Profit Factor: {result.metrics.get('profit_factor', 'N/A')}")
        print(f"  Expectancy: {result.metrics.get('expectancy', 'N/A')}")
        print(f"  Max Drawdown: {result.metrics.get('max_drawdown', 'N/A')}")
    
    # Print quality flags
    if result.quality_flags:
        print("\nQuality Flags:")
        for flag in result.quality_flags:
            print(f"  - {flag}")
    
    # Print artifact paths
    if result.artifact_paths:
        print("\nArtifacts:")
        for path in result.artifact_paths:
            print(f"  - {path}")
    
    # Print stage summary
    if result.stage_results:
        print("\nStage Summary:")
        for stage in result.stage_results:
            status_icon = "✓" if stage.status in ("completed", "passed") else "✗"
            print(f"  {status_icon} {stage.stage_name}: {stage.status}")
            if stage.message:
                print(f"      {stage.message}")
            if stage.error_code:
                print(f"      Error: {stage.error_code}")
    
    # Print warnings
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    # Print errors
    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")
    
    # Print next actions
    if result.next_actions:
        print("\nNext Actions:")
        for action in result.next_actions:
            print(f"  - {action}")
    
    print("=" * 80)
    
    # Print final marker based on status
    if result.status == "completed":
        print("\nREAL_BASELINE_EVALUATION_PASSED")
    elif result.status == "confirmation_required":
        print("\nREAL_BASELINE_EVALUATION_CONFIRMATION_REQUIRED")
    elif result.status == "failed_controlled":
        print("\nREAL_BASELINE_EVALUATION_FAILED_CONTROLLED")
    else:
        print(f"\nREAL_BASELINE_EVALUATION_STATUS: {result.status}")
    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        # Build request
        request = build_request(args)
        
        # Create service
        service = BaselineEvaluationService(
            run_repository=None,  # Will be created by service
            run_stage_repository=None,  # Will be created by service
            artifact_repository=None,  # Will be created by service
            log_repository=None,  # Will be created by service
            audit_repository=None,  # Will be created by service
            strategy_service=None,  # Will be created by service
            config_generator=None,  # Will be created by service
            data_service=None,  # Will be created by service
            backtest_runner=None,  # Will be created by service
            result_parser=None,  # Will be created by service
            decision_service=None,  # Will be created by service
            project_root=None,  # Will be created by service
        )
        
        # Run evaluation
        print(f"\nStarting baseline evaluation for strategy: {args.strategy}")
        print(f"Pairs: {', '.join(request.pairs)}")
        print(f"Timeframe: {request.timeframe}")
        print(f"Days: {request.days}")
        print(f"Risk Profile: {request.risk_profile}")
        print(f"Download Missing Data: {request.download_missing_data}")
        print(f"User Confirmed: {request.user_confirmed}")
        print(f"Apply Decision to Run: {request.apply_decision_to_run}")
        print("\n")
        
        result = service.evaluate(request)
        
        # Print result
        print_result(result)
        
        # Exit with appropriate code
        if result.status == "completed":
            sys.exit(0)
        elif result.status == "confirmation_required":
            sys.exit(1)
        elif result.status == "failed_controlled":
            sys.exit(2)
        else:
            sys.exit(3)
            
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        print("\nREAL_BASELINE_EVALUATION_FAILED_SYSTEM")
        sys.exit(4)


if __name__ == "__main__":
    main()
