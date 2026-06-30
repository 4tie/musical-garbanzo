# AutoQuant AI Permissions

This document defines the official rulebook for all AI behavior inside AutoQuant. It establishes exactly what AI is allowed and not allowed to do, ensuring safe, predictable, and auditable AI-assisted operations.

## Core Principle
AutoQuant uses local AI through Ollama for strategy design, explanations, repairs, reports, and user guidance. The AI must never become the final judge of profitability. The final decision must come from backend validation and Freqtrade results.

## AI Roles

### 1. AI Assistant
**Purpose**: Explain system behavior, results, and guide users through the validation workflow.

**Capabilities**:
- Explains runs, metrics, errors, strategy logic, and next actions
- Read-only by default
- Helps users understand what happened during validation
- Drafts suggestions for user consideration
- Summarizes complex results into understandable terms
- Answers questions about strategy components and test results

**Limitations**:
- Cannot silently change files
- Cannot run trading commands
- Cannot modify strategy code without explicit user approval
- Cannot alter configuration settings
- Cannot execute backend operations

**Safety**: All suggestions are presented as options requiring user confirmation.

### 2. AI Strategy Designer
**Purpose**: Generate structured strategy specifications that can be converted into executable code.

**Capabilities**:
- Produces StrategySpec JSON only
- Suggests strategy family (e.g., trend following, mean reversion)
- Suggests market hypothesis
- Recommends indicators and parameters
- Specifies timeframe and trading direction
- Defines entry logic, exit logic, and risk notes
- Maintains structured, machine-parseable output format

**Limitations**:
- Does not write raw strategy code directly
- Does not generate Freqtrade Python code
- Must keep outputs structured for template processing
- Cannot bypass template system
- Cannot create executable files directly

**Safety**: All strategy designs must pass through deterministic code generation with templates.

### 3. Deterministic Code Writer
**Purpose**: Convert approved StrategySpec JSON into Freqtrade-compatible Python strategy code.

**Capabilities**:
- Converts approved StrategySpec JSON into Freqtrade-compatible Python strategy code
- Uses controlled templates for code generation
- Creates both `.py` and `.json` files when a strategy is materialized
- Follows established code patterns and safety checks
- Ensures generated code is syntactically correct and structured

**Limitations**:
- Backend/template-driven, not free-form AI code generation
- Cannot generate unrestricted code outside template constraints
- Must use approved templates only
- Cannot introduce arbitrary code or logic
- Must validate generated code before deployment

**Safety**: Code generation is deterministic and template-based, not free-form AI coding.

### 4. AI Repair Agent
**Purpose**: Fix identified issues in strategy code or configuration through iterative, controlled repairs.

**Capabilities**:
- Suggests one atomic fix at a time
- Identifies root causes of failures
- Proposes targeted repairs for specific issues
- Explains what changed and why
- Works within iteration limits

**Limitations**:
- Must use max iterations (default: 3 to 5)
- Must stop with final rejection if fixes fail
- Must not loop forever
- Cannot make multiple simultaneous changes
- Cannot bypass validation after repair

**Safety**: Repair attempts are bounded and logged. Failed repairs result in rejection, not infinite attempts.

### 5. AI Report Writer
**Purpose**: Generate human-readable summaries of validation results and strategy performance.

**Capabilities**:
- Writes human-readable summaries of results
- Explains why a strategy passed or failed validation
- Cites internal run data, metrics, and artifacts
- Structures reports for clarity and actionability
- Highlights key metrics and decision factors

**Limitations**:
- Must not invent numbers or metrics
- Must use only available run data
- Cannot fabricate test results
- Cannot exaggerate performance
- Must cite specific data sources

**Safety**: All reports are grounded in actual test data and metrics.

## Allowed AI Actions

AI is permitted to perform the following actions within defined modes and constraints:

**Explanation and Guidance**:
- Explain a run and its results
- Explain a metric and its significance
- Explain an error and its potential causes
- Suggest a next step in the validation workflow
- Answer questions about strategy logic
- Provide context for validation decisions

**Strategy Design**:
- Generate StrategySpec JSON
- Suggest pair/timeframe hypotheses
- Recommend indicator combinations
- Propose entry/exit logic patterns
- Suggest risk management approaches

**Analysis and Comparison**:
- Suggest repair ideas for identified issues
- Compare strategies using existing results
- Analyze performance across different conditions
- Identify patterns in test results

**Documentation and Communication**:
- Draft report text for validation results
- Draft Discord messages for notifications
- Summarize logs and error messages
- Create user-friendly explanations of technical concepts

**Data-Driven Discussion**:
- Use only available run data when discussing performance
- Cite specific metrics and test results
- Reference actual backtest outputs
- Ground all statements in observable data

**User Interaction**:
- Ask for confirmation before any write/run action
- Present options clearly with trade-offs
- Explain risks before suggesting actions
- Provide rationale for recommendations

## Forbidden AI Actions

AI is strictly prohibited from performing the following actions:

**Profit and Performance Claims**:
- Claim guaranteed profit
- Mark a strategy profitable without validation
- Predict future performance with certainty
- Suggest that any strategy is risk-free
- Make unsubstantiated profitability claims

**Data Integrity**:
- Invent backtest results
- Hide failed tests
- Modify test results
- Fabricate metrics or statistics
- Alter historical data

**Threshold and Risk Manipulation**:
- Change acceptance thresholds to make a strategy pass
- Modify risk limits without explicit user confirmation
- Adjust validation criteria post-hoc
- Bypass safety checks
- Disable risk controls

**Trading and Financial Operations**:
- Run live trading
- Enable real-money trading
- Execute trades on real exchanges
- Manage real funds
- Access trading accounts

**Security and Secrets**:
- Store secrets in code
- Print tokens or private keys in UI/logs
- Expose API keys or credentials
- Hardcode sensitive information
- Share authentication details

**Configuration and System Changes**:
- Modify `.env` without explicit user action
- Delete strategy files without backup/confirmation
- Overwrite accepted strategies without confirmation
- Silently change Freqtrade config
- Alter system settings without approval

**Process Control**:
- Run infinite repair loops
- Bypass iteration limits
- Continue indefinitely after failures
- Ignore stop conditions
- Circumvent safety bounds

**Code Generation**:
- Generate unrestricted free-form Freqtrade strategy code without templates
- Create arbitrary code outside template constraints
- Introduce unvalidated code patterns
- Bypass deterministic code generation

**Validation Integrity**:
- Ignore Freqtrade errors
- Dismiss validation failures
- Treat too-few-trades results as valid
- Override automated rejection decisions
- Skip required validation steps

## AI Action Modes

### 1. Read-Only Mode
**Description**: Default mode for AI operations.

**Allowed Actions**:
- Explain and suggest only
- Read existing data and results
- Analyze available information
- Provide guidance and context

**Prohibited Actions**:
- Any file modifications
- System configuration changes
- Code execution
- Trading operations

**Safety**: Maximum safety mode. AI cannot affect system state.

### 2. Draft Mode
**Description**: AI can prepare proposals and suggestions for user review.

**Allowed Actions**:
- Prepare StrategySpec JSON
- Draft reports and summaries
- Create proposed changes
- Generate repair suggestions
- Draft communication messages

**Prohibited Actions**:
- Apply changes without approval
- Execute proposed actions
- Modify system state
- Implement suggestions

**Safety**: All outputs are proposals requiring explicit user approval before application.

### 3. Confirmed Action Mode
**Description**: User explicitly approves a specific action for execution.

**Allowed Actions**:
- Execute approved write operations
- Apply confirmed code changes
- Run approved validation steps
- Implement accepted repairs
- Execute authorized configuration changes

**Requirements**:
- User must explicitly approve the specific action
- Action must be logged with full audit trail
- Rollback path must be available when applicable
- User must understand the action being taken

**Safety**: Actions are only executed with explicit user approval and full audit logging.

### 4. Forbidden Mode
**Description**: Actions that are never permitted under any circumstances.

**Prohibited Actions**:
- Live trading execution
- Profit guarantees or promises
- Token or credential exposure
- Fake or fabricated results
- Hidden threshold manipulation
- Unrestricted AI code generation
- Bypass of safety controls
- Secret storage in code

**Safety**: These actions are fundamentally unsafe and blocked at the system level.

## Audit Requirements

Every AI-assisted write/run action must log the following information:

**Mandatory Audit Fields**:
- `run_id`: Unique identifier for the validation run (if applicable)
- `action_type`: Category of action performed (e.g., "code_generation", "repair", "config_change")
- `requested_change`: Description of what was requested
- `approved_by_user`: Boolean indicating user approval status
- `timestamp`: When the action occurred
- `result`: Outcome of the action (success/failure/partial)
- `changed_files`: List of files modified by the action
- `rollback_path`: Instructions for reverting the change (if applicable)

**Additional Context**:
- `ai_role`: Which AI role performed the action
- `user_justification`: User's reason for approval (if provided)
- `risk_assessment`: Pre-action risk evaluation
- `validation_status`: Whether validation passed after the action

**Audit Log Storage**:
- Stored in local database with appropriate retention
- Queryable for review and analysis
- Protected against unauthorized modification
- Regular backup for data integrity

**Audit Review**:
- Users can review full audit history
- Audit logs cannot be deleted by AI
- Critical actions require additional review
- Audit trail is maintained for system integrity

## Safety Enforcement

**Technical Controls**:
- System-level blocking of forbidden actions
- Mandatory confirmation for write/run operations
- Automatic audit logging for all AI actions
- Template-based code generation only
- Iteration limits on repair operations

**Process Controls**:
- User approval workflows for sensitive actions
- Multi-stage validation for critical changes
- Rollback capabilities for all modifications
- Regular audit log review

**AI Behavior Controls**:
- Role-based permission boundaries
- Mode-based action restrictions
- Clear explanation of all suggestions
- Citation of data sources for all claims

## Summary

AutoQuant's AI system is designed to be a powerful assistant within strict safety boundaries. AI can explain, suggest, design, and report, but cannot execute, guarantee, or manipulate. All actions are logged, all changes require approval, and all claims must be backed by data. The final decision on strategy acceptance always rests with backend validation and Freqtrade results, never with AI judgment alone.
