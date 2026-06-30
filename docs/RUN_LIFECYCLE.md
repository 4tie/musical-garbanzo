# AutoQuant Run Lifecycle

This document defines the complete lifecycle of an AutoQuant run, explaining exactly how a strategy moves from user input to final decision and export.

## Run Starting Modes

AutoQuant supports three primary modes for initiating a validation run:

### 1. Upload Existing Strategy
**Purpose**: Validate and improve an existing Freqtrade strategy.

**Process**:
- User uploads or selects a Freqtrade `.py` strategy file
- App validates the file structure and syntax
- App extracts strategy metadata:
  - Class name
  - Timeframe (if present in strategy)
  - Can_short setting (if present)
  - Strategy parameters
  - ROI settings
  - Stoploss configuration
  - Trailing stop settings
  - Indicators where detectable
- App checks whether matching `.json` sidecar exists
- If `.json` is missing:
  - App creates a safe initial `.json` sidecar with default parameters
  - App asks user to confirm generation or provides manual configuration option
- Strategy enters validation workflow at Stage 1

**Use Cases**:
- User has existing strategy to validate
- User wants to test strategy modifications
- User needs to repair broken strategy
- User wants to optimize existing parameters

### 2. Generate New Strategy with AI
**Purpose**: Create a new strategy from scratch using AI guidance.

**Process**:
- User provides strategy specifications:
  - Style (trend following, mean reversion, momentum, etc.)
  - Direction (long, short, or both)
  - Risk profile (conservative, moderate, aggressive)
  - Pair mode (manual selection or auto universe)
  - Timeframe mode (manual selection or auto discovery)
- AI Strategy Designer creates StrategySpec JSON only:
  - Strategy family and market hypothesis
  - Recommended indicators and parameters
  - Entry and exit logic
  - Risk management notes
  - Timeframe and trading direction
- Backend validates StrategySpec structure and completeness
- Deterministic templates generate:
  - Freqtrade-compatible `.py` strategy file
  - Matching `.json` parameter sidecar file
- Strategy enters validation workflow at Stage 1

**Use Cases**:
- User wants to explore new strategy ideas
- User needs starting point for strategy development
- User wants AI-assisted strategy design
- User is building strategy from market hypothesis

### 3. Repair Previous Strategy
**Purpose**: Fix identified issues in a failed or rejected strategy.

**Process**:
- User selects a failed run or rejected strategy from history
- App loads failure reasons and diagnostic information
- AI Repair Agent analyzes the failure:
  - Identifies root cause
  - Proposes one atomic fix at a time
  - Explains what changed and why
- Backend applies fix only after:
  - Explicit user confirmation, OR
  - Allowed auto-fix mode (if configured)
- New run is created as a child run of the failed parent
- Retry history is linked for traceability
- Repair attempts are bounded (default: 3-5 iterations)
- If repairs fail after max iterations, final rejection is issued

**Use Cases**:
- Strategy failed validation with fixable issues
- User wants to improve rejected strategy
- Strategy has runtime errors or bugs
- Parameters need adjustment based on test results

## Official Run Stages

### Stage 0 — Run Setup
**Purpose**: Initialize the run with all necessary configuration and context.

**Actions**:
- Create unique `run_id` for tracking
- Save user selections and preferences
- Save starting mode (upload/generate/repair)
- Save strategy source (file path or AI generation)
- Save risk profile configuration
- Save timeframe mode and selection
- Save pair mode and selection
- Save exchange configuration
- Save timerange for backtesting
- Save initial status as `created`

**Output**: Fully configured run ready for pre-flight checks

### Stage 1 — Pre-flight Checks
**Purpose**: Verify system readiness before executing resource-intensive operations.

**Checks**:
- Freqtrade installation and path validation
- Python environment and dependency verification
- Strategy file existence and accessibility
- Strategy import safety check (no malicious code)
- Config generation capability
- `.env` required keys existence (without exposing values)
- Ollama connection if AI features are needed
- Discord configuration if notifications are enabled
- Disk space availability for data and results
- Exchange API connectivity (if needed for data download)

**Failure Handling**:
- Any check failure results in `failed_system` status
- Clear error messages guide user to resolution
- Run does not proceed to resource-intensive stages
- **Controlled Failure:** Failures use specific error codes with user-facing messages
- **Controlled Failure:** Error codes map to next_actions for user guidance
- **Controlled Failure:** No stack traces in API-safe responses
- **Controlled Failure:** No secrets in errors or details

### Stage 2 — Strategy Normalization
**Purpose**: Ensure strategy is properly structured and stored in the workspace.

**Actions**:
- Ensure strategy is stored in local strategy workspace
- Verify `.py` strategy file exists and is valid
- Ensure `.json` sidecar file exists
- Extract and validate strategy metadata:
  - Class name conforms to Freqtrade standards
  - Timeframe is valid Freqtrade format
  - Direction (long, short, or both) is properly set
  - Minimal ROI configuration is valid
  - Stoploss configuration is present and reasonable
  - Trailing stop settings are properly configured
  - Protection settings are valid
  - Custom parameters are properly defined

**Validation**:
- Strategy structure must pass Freqtrade import test
- Parameters must be within acceptable ranges
- Configuration must be complete and consistent

### Stage 3 — Pair and Timeframe Selection
**Purpose**: Determine the trading universe and testing timeframe.

**Pair Selection**:
- **Manual pairs mode**:
  - Validate each selected pair exists on exchange
  - Check pair format and quote currency consistency
  - Store selected pairs with user-specified reason
- **Auto universe mode**:
  - Generate candidate pair universe based on:
    - Configured exchange
    - Quote currency (e.g., USDT, BTC)
    - Volume and liquidity thresholds
    - User-defined filters (if any)
  - Store generated universe with generation criteria

**Timeframe Selection**:
- **Manual timeframe mode**:
  - Validate timeframe is valid Freqtrade format
  - Check timeframe is appropriate for strategy style
  - Store selected timeframe with user reason
- **Auto timeframe discovery mode**:
  - Test candidate timeframes using policy rules
  - Evaluate based on:
    - Trade count potential
    - Signal frequency
    - Market noise considerations
  - Select optimal timeframe based on scoring
  - Store selection with discovery rationale

**Output**: Validated pairs and timeframe for testing

### Stage 4 — Data Availability Check
**Purpose**: Ensure required historical data is available for backtesting.

**Actions**:
- Check local Freqtrade historical data for:
  - Selected exchange
  - Selected pairs
  - Selected timeframe
  - Specified timerange
- Assess data completeness and quality

**Data Handling**:
- **If data is available and complete**:
  - Proceed to backtesting stage
- **If data is missing and auto-download is enabled**:
  - Run Freqtrade data download command
  - Download required data for all pairs
  - Validate downloaded data quality
  - Proceed to backtesting stage
- **If data is missing and auto-download is disabled**:
  - Stop with `failed_controlled` status
  - Use error code `data_missing` with user-facing message
  - Provide next_actions for user guidance
  - Never reject strategy quality before confirming data availability
- **If data is missing and user_confirmed=false**:
  - Stop with `confirmation_required` status
  - Use error code `confirmation_required_for_download`
  - Provide next_actions to enable confirmation

**Controlled Failure Behavior**:
- Data failures use specific error codes (e.g., `data_missing`, `confirmation_required_for_download`, `data_download_failed`)
- Error codes map to user-facing messages with next_actions
- Pipeline stops before backtest if data issues are unresolved
- No stack traces in API-safe responses
- No secrets in errors or details

**Critical Rule**: Data availability issues are system failures, not strategy rejections.

### Stage 5 — Baseline Backtest
**Purpose**: Execute initial backtesting to establish baseline performance metrics.

**Actions**:
- Run Freqtrade backtest with baseline parameters
- Capture complete stdout and stderr output
- Save raw result files from Freqtrade
- Parse and extract key metrics:
  - Overall performance metrics
  - Pair-level performance breakdown
  - Trade count and frequency
  - Net profit (absolute and percentage)
  - Profit Factor
  - Maximum drawdown
  - Win rate
  - Average win and average loss
  - Expectancy calculation
  - Sharpe ratio (if available)
  - Calmar ratio (if available)

**Controlled Failure Behavior**:
- Backtest failures use specific error codes (e.g., `backtest_failed`)
- Error codes map to user-facing messages with next_actions
- Raw stdout/stderr artifacts are preserved for inspection
- Pipeline stops before parsing if backtest fails
- No stack traces in API-safe responses

**Data Storage**:
- Raw backtest results archived
- Parsed metrics stored in database
- Trade-by-trade results preserved
- Performance charts generated if available

### Stage 6 — Initial Decision Gate
**Purpose**: Evaluate baseline results and determine if strategy deserves further validation.

**Evaluation Criteria**:
- **No trades generated**:
  - Reject or repair depending on policy
  - Strategy may have incompatible logic or timeframe
- **Too few trades**:
  - Controlled failure or repair path
  - Trade count below statistical significance threshold
- **Negative expectancy**:
  - Reject or repair
  - Strategy loses money on average per trade
- **Excessive drawdown**:
  - Reject or repair
  - Risk exceeds acceptable thresholds
- **Metrics pass initial thresholds**:
  - Promote to `candidate` status
  - Proceed to additional validation stages

**Decision Logic**:
- Each failure reason is clearly documented
- Repair suggestions are provided when applicable
- User can adjust thresholds or request repair
- Strategies passing proceed to deeper validation

### Stage 7 — Hyperopt When Needed
**Purpose**: Optimize strategy parameters when enabled by policy.

**Conditions**:
- Only run hyperopt when explicitly allowed by policy
- User must enable optimization for the run
- Strategy must have passed initial decision gate

**Optimization Rules**:
- Do not optimize too many parameters at once
- Respect locked parameters (user-specified fixed values)
- Respect `optimize=False` flags in strategy
- Limit optimization space to prevent overfitting
- Use appropriate hyperopt strategy (random, grid, etc.)

**Process**:
- Run Freqtrade hyperopt with defined parameter space
- Save all trials for analysis
- Identify best parameters based on objective function
- Compare before/after performance
- Validate optimized parameters don't overfit

**Validation**:
- Do not accept optimized results without validation
- Optimized strategy must pass backtesting again
- Compare optimized vs baseline performance
- Check for overfitting indicators

### Stage 8 — Walk-Forward / Out-of-Sample Validation
**Purpose**: Validate strategy performance on unseen data to detect overfitting.

**Data Splitting**:
- Split historical data into:
  - In-sample (training) period
  - Out-of-sample (validation) period
- Use rolling windows for walk-forward analysis
- Maintain sufficient data in each period

**Process**:
- Optimize or train strategy only on in-sample data
- Test optimized parameters on out-of-sample data
- Store window-level results for each period
- Compare in-sample vs out-of-sample performance

**Failure Criteria**:
- Fail if performance collapses badly out-of-sample
- Significant degradation indicates overfitting
- OOS performance must meet minimum thresholds
- Performance consistency across windows is required

**Output**:
- Walk-forward analysis results
- OOS performance metrics
- Overfitting assessment
- Stability evaluation

### Stage 9 — Robustness Checks
**Purpose**: Evaluate strategy stability under varying conditions and parameters.

**Multi-Pair Validation**:
- If pair universe mode is enabled:
  - Test strategy across multiple pairs
  - Evaluate performance consistency
  - Identify pair-specific vs general performance
  - Fail strategies that only work on specific pairs

**Sensitivity Testing**:
- Test around key parameters:
  - Vary parameters by small percentages
  - Evaluate performance sensitivity
  - Identify fragile parameter combinations
  - Require reasonable parameter stability

**Safety Checks**:
- Lookahead safety check when available:
  - Verify no future data leakage
  - Check indicator calculation timing
  - Validate signal generation timing
- Recursive indicator safety check when available:
  - Check for recursive calculation issues
  - Verify indicator independence
  - Validate no circular dependencies

**Market Regime Analysis**:
- Evaluate performance across different market conditions:
  - Trending vs ranging markets
  - High volatility vs low volatility periods
  - Bull vs bear market phases
- Note regime stability and dependencies

**Failure Criteria**:
- Fail unstable strategies
- Reject strategies with high parameter sensitivity
- Reject strategies that fail safety checks
- Reject strategies with regime-specific performance only

### Stage 10 — Final Classification
**Purpose**: Assign final status based on comprehensive validation results.

**Classification Levels**:

**Rejected**:
- Failed core validation requirements
- Insufficient data or trades
- Negative metrics or excessive risk
- Safety issues or overfitting
- Failed robustness checks

**Candidate**:
- Passed basic minimum thresholds
- Positive net profit after fees
- Trade count meets minimum requirements
- Needs additional validation
- Not ready for deployment

**Promising**:
- Better metrics than Candidate
- Passed additional validation checks
- Stronger performance indicators
- Still needs WFA/OOS/robustness confirmation

**Validated**:
- Passed core backtest with strong metrics
- Passed out-of-sample validation
- Passed walk-forward analysis
- Passed robustness checks
- Can be exported for manual review or dry-run testing

**Approved**:
- Highest internal classification
- Strongest evidence available in AutoQuant
- Excellent performance across all dimensions
- Consistent behavior in all tests
- Best available candidate for deployment

**Stored Information**:
- Final status and classification
- Detailed reasons for classification
- Comprehensive metrics summary
- List of failed validation gates
- List of passed validation gates
- Confidence score based on evidence strength
- Next recommended action for user

### Stage 11 — Export
**Purpose**: Generate exportable artifacts for strategies that qualify.

**Export Conditions**:
- Strategy must be classified as Validated or Approved
- User must approve export
- All validation artifacts must be complete

**Exported Files**:
- `StrategyName.py` - Freqtrade-compatible strategy file
- `StrategyName.json` - Matching parameter sidecar file
- Decision report - Comprehensive validation summary
- Run metadata - Complete run information and provenance
- Optional: Freqtrade config - Ready-to-use configuration file
- Optional: Performance charts - Visual performance representation

**Export Location**:
- Defined export directory in user configuration
- Clear folder structure for organization
- Exact output folder path shown to user
- Overwrite protection for existing files

**Export Verification**:
- Verify exported files are valid
- Confirm file integrity
- Validate Freqtrade can import exported strategy
- Generate export confirmation

### Stage 12 — Notification
**Purpose**: Keep user informed of run progress and results via Discord.

**Notification Triggers**:
- Run started message
- Stage failure message (if applicable)
- Major milestone completion
- Final result message
- Export completion message

**Message Content**:
- Concise status updates
- Key metrics and decisions
- Actionable next steps
- Links to detailed reports

**Security Rules**:
- Never send secrets or API keys
- Never send sensitive configuration data
- Never expose private information
- Keep messages focused on run status

**Notification Control**:
- User can enable/disable notifications
- User can configure notification frequency
- User can specify which events trigger notifications

## Run States

AutoQuant runs progress through the following states:

- `created` - Run initialized with configuration, ready for pre-flight checks
- `queued` - Run is queued waiting for system resources
- `running` - Run is actively executing validation stages
- `waiting_for_confirmation` - Run paused awaiting user decision or approval
- `failed_controlled` - Run failed due to expected issues (data, configuration, etc.)
- `failed_system` - Run failed due to system errors (environment, dependencies, etc.)
- `rejected` - Strategy failed validation and is not viable
- `candidate` - Strategy passed basic thresholds, needs more validation
- `promising` - Strategy shows strong performance, needs confirmation tests
- `validated` - Strategy passed all validation gates, ready for export
- `approved` - Strategy achieved highest classification, ready for deployment
- `exported` - Strategy artifacts have been successfully exported
- `cancelled` - Run was cancelled by user or system intervention

## Parent/Child Run Relationships

AutoQuant maintains hierarchical relationships between related runs:

**Repair Runs**:
- A repair run links to the failed parent run
- Parent run ID is stored in child run metadata
- Repair history is traceable through the chain
- Each repair attempt is a separate child run
- Final approved strategy links back to original failed run

**Optimization Runs**:
- An optimization run links to the baseline run
- Baseline parameters are preserved for comparison
- Optimized results reference the original baseline
- Multiple optimization attempts can branch from same baseline
- Best optimization is selected based on validation criteria

**Export Links**:
- Export links to the final approved run
- Export artifacts reference the source run
- Export metadata includes complete provenance
- Exported strategies can be traced back to validation results

**Relationship Storage**:
- `parent_run_id` - ID of the parent run (if applicable)
- `run_type` - Type of run (baseline, repair, optimization, etc.)
- `generation` - Depth in run hierarchy (0 for original, 1 for first child, etc.)
- `relationship_reason` - Why this run was created from the parent

**Benefits**:
- Complete audit trail of strategy evolution
- Ability to compare different approaches
- Understanding of what changes improved results
- Rollback capability to previous versions
- Analysis of repair and optimization effectiveness

## Summary

The AutoQuant run lifecycle provides a structured, comprehensive path from strategy idea to validated export. Each stage has clear purpose, validation criteria, and failure handling. The system maintains full traceability through run states and parent/child relationships. No stage is skipped, and all decisions are backed by data and validation rules. The lifecycle ensures that only strategies passing rigorous, multi-dimensional validation can achieve export and deployment consideration.
