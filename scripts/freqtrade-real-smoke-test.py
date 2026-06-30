#!/usr/bin/env python3
"""
Real Freqtrade Smoke Test for HER Integration

This script validates HER's Freqtrade integration against real Freqtrade,
real data download, and real backtesting.

SAFETY: This script never:
- Runs live trading (freqtrade trade)
- Runs webserver (freqtrade webserver)
- Uses exchange keys
- Sets dry_run to false
- Uses --erase flag
- Calls Ollama
- Sends Discord messages

Exit codes:
- 0: Smoke test passed
- 1: Freqtrade not configured
- 2: Workspace validation failed
- 3: Data download failed
- 4: Backtest failed
- 5: Unexpected error
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.services.freqtrade_detection import FreqtradeDetectionService
from app.services.freqtrade_strategy_service import FreqtradeStrategyService
from app.services.freqtrade_data_service import FreqtradeDataService
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator
from app.services.freqtrade_backtest_runner import FreqtradeBacktestRunner
from app.repositories.runs import RunRepository
from app.repositories.logs import RunLogRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.artifacts import ArtifactRepository
from app.schemas.runs import RunCreate
from app.schemas.freqtrade_config import FreqtradeBacktestConfigRequest
from app.schemas.freqtrade_data import FreqtradeDataCheckRequest, FreqtradeDataDownloadRequest
from app.schemas.freqtrade_backtest import FreqtradeBacktestRequest


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(key: str, value: str):
    """Print a key-value result."""
    print(f"  {key}: {value}")


def step_a_environment_and_version():
    """Step A: Check Freqtrade availability and version."""
    print_section("Step A: Environment and Version Check")
    
    detector = FreqtradeDetectionService()
    status = detector.get_status()
    
    if not status.configured:
        print_result("Status", "FAILED")
        print_result("Reason", "REAL_SMOKE_PENDING: Freqtrade not configured")
        print_result("Action", "Set FREQTRADE_PATH or install freqtrade in PATH")
        sys.exit(1)
    
    print_result("Freqtrade Configured", "Yes")
    print_result("Executable", str(status.executable_path) if status.executable_path else "N/A")
    
    # Get version
    version_result = detector.get_version()
    if version_result.available and version_result.command_result:
        print_result("Version", version_result.command_result.stdout.strip())
    else:
        print_result("Version", "Unknown (command failed)")
        if version_result.error:
            print_result("Version Error", version_result.error)
    
    return status


def step_b_workspace(status):
    """Step B: Validate workspace."""
    print_section("Step B: Workspace Validation")
    
    workspace_valid = status.workspace_valid
    print_result("Workspace Valid", str(workspace_valid))
    
    if not workspace_valid:
        print_result("Status", "FAILED")
        print_result("Reason", "Workspace directories not valid")
        sys.exit(2)
    
    # Check smoke strategy exists
    smoke_strategy_path = settings.freqtrade_user_data_dir_path / "strategies" / "HERSmokeStrategy.py"
    print_result("Smoke Strategy Path", str(smoke_strategy_path))
    print_result("Smoke Strategy Exists", str(smoke_strategy_path.exists()))
    
    if not smoke_strategy_path.exists():
        print_result("Status", "FAILED")
        print_result("Reason", "Smoke strategy file not found")
        sys.exit(2)
    
    # Check config directory
    config_dir = settings.freqtrade_config_dir_path
    print_result("Config Directory", str(config_dir))
    print_result("Config Directory Exists", str(config_dir.exists()))
    
    return smoke_strategy_path


def step_c_create_run():
    """Step C: Create HER run record."""
    print_section("Step C: Create HER Run Record")
    
    run_repo = RunRepository()
    
    run_data = RunCreate(
        name="Real Freqtrade Smoke Test",
        mode="manual_test",
        status="running",
        exchange="binance",
        quote_currency="USDT",
        trading_mode="spot",
        timeframe="5m",
        pairs=["BTC/USDT"],
        risk_profile="conservative",
        analysis_depth="quick",
        is_demo=False
    )
    
    run = run_repo.create_run(run_data)
    print_result("Run ID", run["id"])
    print_result("Run Name", run["name"])
    print_result("Run Status", run["status"])
    
    # Log smoke started
    log_repo = RunLogRepository()
    # log_repo.create equivalent: RunLogRepository writes through add_log.
    log_repo.add_log(
        run_id=run["id"],
        level="info",
        source="system",
        message="Real Freqtrade smoke test started"
    )
    
    return run


def step_d_generate_smoke_config(run):
    """Step D: Generate smoke config."""
    print_section("Step D: Generate Smoke Config")
    
    config_generator = FreqtradeConfigGenerator()
    
    config_request = FreqtradeBacktestConfigRequest(
        run_id=run["id"],
        strategy_name="HERSmokeStrategy",
        pairs=["BTC/USDT"],
        timeframe="5m",
        exchange="binance",
        trading_mode="spot",
        stake_currency="USDT",
        data_format_ohlcv="feather",
    )
    config_result = config_generator.write_backtest_config(config_request)
    config_path = Path(config_result.config_path) if config_result.config_path else None
    
    print_result("Config Path", str(config_path) if config_path else "N/A")
    print_result("Config Generated", str(config_result.success))
    
    if not config_result.success:
        print_result("Status", "FAILED")
        print_result("Reason", config_result.error or "Unknown error")
        return None, None
    
    return config_path, config_path


def step_e_download_data(run):
    """Step E: Download small real candle dataset."""
    print_section("Step E: Download Real Data")
    
    data_service = FreqtradeDataService()
    
    request = FreqtradeDataDownloadRequest(
        exchange="binance",
        trading_mode="spot",
        pairs=["BTC/USDT"],
        timeframes=["5m"],
        days=30,
        timerange=None,
        data_format_ohlcv="feather",
        user_confirmed=True  # Script explicitly confirms
    )
    
    print_result("Exchange", request.exchange)
    print_result("Pair", ", ".join(request.pairs))
    print_result("Timeframe", ", ".join(request.timeframes))
    print_result("Days", str(request.days))
    print_result("Data Format", request.data_format_ohlcv)
    
    download_result = data_service.download_data(
        request=request,
    )
    
    print_result("Download Success", str(download_result.success))
    print_result("Blocked", str(download_result.blocked))
    
    if not download_result.success:
        print_result("Status", "FAILED")
        print_result("Reason", download_result.stderr or "Unknown error")
        print_result("Error Type", "REAL_SMOKE_FAILED_DATA_DOWNLOAD")
        return False
    
    # Log data download completed
    log_repo = RunLogRepository()
    log_repo.add_log(
        run_id=run["id"],
        level="info",
        source="system",
        message="Data download completed successfully"
    )
    
    return True


def step_f_verify_data():
    """Step F: Verify data availability."""
    print_section("Step F: Verify Data")
    
    data_service = FreqtradeDataService()
    
    check_request = FreqtradeDataCheckRequest(
        exchange="binance",
        trading_mode="spot",
        pairs=["BTC/USDT"],
        timeframe="5m",
        timerange=None,
        show_timerange=True,
    )
    
    check_result = data_service.check_data(check_request)
    available = any(pair.exists for pair in check_result.pairs)
    
    print_result("Data Available", str(available))
    print_result("Data Source", check_result.source)
    
    if not available:
        print_result("Status", "FAILED")
        print_result("Reason", "Data not available after download")
        return False
    
    return True


def step_g_run_backtest(run, config_path):
    """Step G: Run real backtest."""
    print_section("Step G: Run Real Backtest")
    
    backtest_runner = FreqtradeBacktestRunner()
    
    request = FreqtradeBacktestRequest(
        run_id=run["id"],
        config_path=str(config_path),
        strategy_name="HERSmokeStrategy",
        timeframe="5m",
        export="trades",
        pairs=["BTC/USDT"],
        user_confirmed=True  # Script explicitly confirms
    )
    
    print_result("Strategy", request.strategy_name)
    print_result("Timeframe", request.timeframe)
    print_result("Export Type", request.export)
    print_result("Config Path", request.config_path)
    
    backtest_result = backtest_runner.run_backtest(request)
    
    print_result("Backtest Success", str(backtest_result.success))
    print_result("Exit Code", str(backtest_result.exit_code) if backtest_result.exit_code is not None else "N/A")
    print_result("Duration", f"{backtest_result.duration_seconds:.2f}s" if backtest_result.duration_seconds else "N/A")
    
    if not backtest_result.success:
        print_result("Status", "FAILED")
        print_result("Reason", backtest_result.error or "Unknown error")
        return None, backtest_result
    
    # Log backtest completed
    log_repo = RunLogRepository()
    log_repo.add_log(
        run_id=run["id"],
        level="info",
        source="system",
        message="Backtest completed successfully"
    )
    
    return backtest_result.artifacts, backtest_result


def step_h_capture_artifacts(run, backtest_result):
    """Step H: Capture artifacts and update run status."""
    print_section("Step H: Capture Artifacts")
    
    artifact_repo = ArtifactRepository()
    audit_repo = AuditLogRepository()
    log_repo = RunLogRepository()
    
    artifact_count = 0
    
    # Register backtest artifacts if available
    if backtest_result and backtest_result.artifacts:
        for artifact in backtest_result.artifacts:
            from app.schemas.artifacts import ArtifactCreate
            artifact_repo.create_artifact(
                ArtifactCreate(
                    run_id=run["id"],
                    strategy_id=None,
                    artifact_type="backtest_raw",
                    file_path=artifact.path,
                    description=f"Backtest artifact: {artifact.artifact_type}"
                )
            )
            artifact_count += 1
    
    print_result("Artifacts Registered", str(artifact_count))
    
    # Update run status
    run_repo = RunRepository()
    if backtest_result and backtest_result.success:
        run_repo.update_status(run["id"], "validated")
        final_status = "validated"
    else:
        run_repo.update_status(run["id"], "failed_controlled")
        final_status = "failed_controlled"
    
    print_result("Final Run Status", final_status)
    
    # Log smoke completed
    log_repo.add_log(
        run_id=run["id"],
        level="info",
        source="system",
        message="Real Freqtrade smoke test completed"
    )
    
    # Audit log
    from app.schemas.audit_logs import AuditLogCreate
    audit_repo.create_audit_log(
        AuditLogCreate(
            actor="system",
            action_type="freqtrade_smoke_test",
            run_id=run["id"],
            description=f"Real Freqtrade smoke test completed with status: {final_status}",
            notes=f"Artifacts registered: {artifact_count}"
        )
    )
    
    return artifact_count, final_status


def step_i_output_summary(run, freqtrade_version, config_path, data_status, 
                         backtest_result, artifact_count, final_status):
    """Step I: Output summary."""
    print_section("Step I: Summary")
    
    print_result("Run ID", run["id"])
    print_result("Freqtrade Version", freqtrade_version)
    print_result("Config Path", str(config_path) if config_path else "N/A")
    print_result("Data Status", "Success" if data_status else "Failed")
    print_result("Backtest Exit Code", str(backtest_result.exit_code) if backtest_result and backtest_result.exit_code is not None else "N/A")
    print_result("Backtest Duration", f"{backtest_result.duration_seconds:.2f}s" if backtest_result and backtest_result.duration_seconds else "N/A")
    print_result("Artifact Count", str(artifact_count))
    print_result("Final HER Run Status", final_status)
    
    if final_status == "validated":
        print("\n✓ REAL_SMOKE_PASSED")
        return 0
    else:
        print("\n✗ REAL_SMOKE_FAILED")
        return 4


def main():
    """Main smoke test execution."""
    print_section("HER Freqtrade Real Smoke Test")
    print(f"Started at: {datetime.now().isoformat()}")
    
    try:
        # Step A: Environment and version
        status = step_a_environment_and_version()
        freqtrade_version = status.version if status.version else "unknown"
        
        # Step B: Workspace
        smoke_strategy_path = step_b_workspace(status)
        
        # Step C: Create run
        run = step_c_create_run()
        
        # Step D: Generate config
        config_path, config_file = step_d_generate_smoke_config(run)
        if config_path is None:
            sys.exit(2)
        
        # Step E: Download data
        data_success = step_e_download_data(run)
        if not data_success:
            # Mark run as failed
            run_repo = RunRepository()
            run_repo.update_status(run["id"], "failed_controlled")
            sys.exit(3)
        
        # Step F: Verify data
        data_verified = step_f_verify_data()
        if not data_verified:
            run_repo = RunRepository()
            run_repo.update_status(run["id"], "failed_controlled")
            sys.exit(3)
        
        # Step G: Run backtest
        artifacts, backtest_result = step_g_run_backtest(run, config_file)
        if backtest_result is None or not backtest_result.success:
            # Step H will handle status update
            step_h_capture_artifacts(run, backtest_result)
            sys.exit(4)
        
        # Step H: Capture artifacts
        artifact_count, final_status = step_h_capture_artifacts(run, backtest_result)
        
        # Step I: Output summary
        exit_code = step_i_output_summary(
            run, freqtrade_version, config_file, 
            data_success, backtest_result, artifact_count, final_status
        )
        
        sys.exit(exit_code)
        
    except Exception as e:
        print_section("UNEXPECTED ERROR")
        print_result("Error Type", type(e).__name__)
        print_result("Error Message", str(e))
        sys.exit(5)


if __name__ == "__main__":
    main()
