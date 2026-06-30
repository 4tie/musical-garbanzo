# AutoQuant UI Blueprint

This document defines the complete user interface blueprint for AutoQuant, providing sufficient detail for frontend developers to build the first complete version.

## Global Layout

### Overall Structure
- **Left sidebar navigation** - Primary navigation and page selection
- **Top status bar** - System status and quick actions
- **Main content area** - Page-specific content and interactions
- **Right-side AI Assistant drawer** - Contextual AI assistance (available from relevant pages)

### Design Principles
- **Dark mode first** - Primary design uses dark theme
- **Clean cards** - Information organized in card-based layout
- **Clear status colors** - Consistent color coding for status indication
- **Live run feedback** - Real-time updates during validation runs
- **No clutter** - Minimal, focused interface
- **Understandable stages** - Every stage comprehensible without reading raw logs

## Top Status Bar

### Status Display
- **App name**: AutoQuant
- **Current active run selector**: Dropdown to select active run
- **Freqtrade status**: Connected (green) / Missing (red)
- **Ollama status**: Connected (green) / Missing (red)
- **Discord bot status**: Connected (green) / Missing (red) / Disabled (gray)
- **SQLite/database status**: Healthy (green) / Error (red)
- **Settings shortcut**: Quick access to configuration
- **"Ask AI" button**: Opens AI Assistant drawer with current context

### Status Indicators
- **Green**: System component healthy and operational
- **Red**: System component missing or error state
- **Gray**: System component disabled or not configured
- **Blue**: System component processing or connecting

## Sidebar Navigation

### Pages/Tabs
1. **Dashboard** - System overview and quick actions
2. **AutoQuant** - Main validation workflow
3. **Strategy Lab** - Strategy design and inspection
4. **Optimizer** - Parameter optimization
5. **Runs** - Historical run management
6. **Results** - Detailed result analysis
7. **Strategy Editor** - Strategy file inspection and editing
8. **AI Assistant** - Interactive AI assistance
9. **Settings** - System configuration

### Navigation Behavior
- Active page highlighted in sidebar
- Click navigation item to switch pages
- Keyboard shortcuts for page switching (optional)
- Collapsible sidebar on smaller screens

## Visual Status Rules

### Color Coding
- **Green**: passed / healthy / approved / connected
- **Amber**: warning / controlled failure / needs review / degraded
- **Red**: failed / rejected / system error / missing
- **Blue**: running / processing / connecting
- **Gray**: pending / skipped / disabled / not configured

### Status Icons
- Checkmark for passed/completed
- X for failed/rejected
- Spinner for running/processing
- Warning triangle for warnings
- Question mark for unknown/pending
- Dash for skipped/not applicable

## Page 1 — Dashboard

### Purpose
Show the user the current state of the whole local system at a glance.

### Sections

#### Welcome / Mission Card
- Brief welcome message
- AutoQuant mission reminder
- Quick system status summary
- "Get Started" call-to-action for new users

#### System Health Cards
Grid layout showing component status:

- **Freqtrade Status**
  - Status: Connected/Missing
  - Version number (if connected)
  - Last heartbeat time
  - Action: Configure if missing

- **Ollama Status**
  - Status: Connected/Missing
  - Model name (if connected)
  - Last query time
  - Action: Configure if missing

- **Discord Bot Status**
  - Status: Connected/Missing/Disabled
  - Channel name (if connected)
  - Last notification time
  - Action: Configure if missing

- **Database Status**
  - Status: Healthy/Error
  - Database size
  - Last backup time
  - Action: Repair if error

- **Data Status**
  - Last data download timestamp
  - Data coverage summary
  - Estimated data freshness
  - Action: Download new data

#### Latest Run Summary
- Run name and ID
- Current status (with color)
- Current stage (if running)
- Progress percentage
- Quick action: View run details

#### Recent Strategies
- List of 3-5 most recently validated strategies
- Strategy name, classification, status
- Quick action: View strategy details

#### Recent Failures
- List of 3-5 most recent failed runs
- Run name, failure reason, timestamp
- Quick action: View failure details / Retry

#### Quick Actions
Button grid for common actions:

- **Start new AutoQuant run** - Navigate to AutoQuant page
- **Upload strategy** - Open strategy upload dialog
- **Generate strategy idea** - Navigate to Strategy Lab
- **Open latest results** - Navigate to Results page
- **Open settings** - Navigate to Settings page

## Page 2 — AutoQuant

### Purpose
Main workflow page where the user starts and monitors a validation run.

### Top Area

#### New Run Button
- Primary action button to create new run
- Opens run configuration panel

#### Run Mode Selector
Radio buttons or dropdown:
- **Upload Existing Strategy** - Upload or select existing `.py` file
- **Generate New Strategy with AI** - Use AI to create new strategy
- **Repair Previous Strategy** - Fix failed or rejected strategy

#### Configuration Fields
- **Run name** - Text input for run identification
- **Exchange selector** - Dropdown (Binance, Kraken, etc.)
- **Quote currency selector** - Dropdown (USDT, BTC, etc.)
- **Timerange selector** - Date range picker or preset (30d, 90d, 1y)
- **Risk profile selector** - Conservative / Balanced / Aggressive
- **Analysis depth selector** - Quick / Standard / Deep

### Strategy Source Card
Conditional display based on run mode:

#### Upload Existing Strategy Mode
- File upload area for `.py` strategy file
- Dropdown to select existing local strategy
- Strategy preview panel (class name, indicators detected)
- Matching `.json` detection (create if missing)
- Validation status indicator

#### Generate New Strategy with AI Mode
- Strategy idea prompt text area
- Style selector (dropdown)
- Direction selector (dropdown)
- "Generate StrategySpec" button
- StrategySpec JSON preview panel
- Template preview
- "Send to AutoQuant" button

#### Repair Previous Strategy Mode
- Failed run selector (dropdown with failure reasons)
- Failure analysis display
- AI repair suggestion panel
- "Apply Repair" button
- Repair history display

### Trading Style Card
Selection options:
- **Scalping** - High-frequency, small profit targets
- **Intraday** - Day trading, no overnight positions
- **Swing** - Multi-day positions
- **Trend following** - Follow market trends
- **Mean reversion** - Trade against extremes
- **Breakout** - Trade breakouts from ranges
- **Custom** - User-defined style

### Direction Card
Radio buttons:
- **Long only** - Buy signals only
- **Short only** - Sell signals only
- **Long and short** - Both directions

### Pairs Card
Two modes:

#### Manual Pairs Mode
- Pair input field (comma-separated or multi-select)
- Add/remove pairs buttons
- Pair validation indicator
- Quote currency consistency check

#### Auto Pair Universe Mode
- Exchange selector
- Quote currency selector
- Volume threshold slider
- Liquidity filter toggle
- "Generate Universe" button
- Generated pairs list with selection reason
- Edit generated universe option

### Timeframe Card
Two modes:

#### Manual Timeframe Mode
- Timeframe dropdown (1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d)
- Timeframe validation indicator

#### Auto Timeframe Discovery Mode
- Candidate timeframes checklist:
  - 1m, 3m, 5m, 15m, 30m, 1h, 4h
- Discovery criteria settings
- "Discover Best Timeframe" button
- Selected timeframe with reasoning
- Rejected timeframes with reasons

### Data Card
- Historical data availability indicator
- Data coverage visualization (timeline)
- Auto-download missing data toggle
- Estimated required data range display
- Download progress bar (when downloading)
- Download logs panel (expandable)

### Start Button
- **"Start AutoQuant Run"** - Primary action button
- Disabled until required inputs are valid
- Validation check on button hover
- Confirmation dialog if action will:
  - Download large amounts of data
  - Overwrite existing generated files
  - Take significant time

### Live Run Area

#### Stage Display Layout
Vertical timeline or horizontal stage cards showing all 13 stages:

1. **Run Setup**
2. **Pre-flight Checks**
3. **Strategy Normalization**
4. **Pair & Timeframe Selection**
5. **Data Availability**
6. **Baseline Backtest**
7. **Initial Decision**
8. **Hyperopt**
9. **Walk-Forward / OOS**
10. **Robustness**
11. **Final Classification**
12. **Export**
13. **Discord Notification**

#### Stage Card Components
Each stage card displays:

- **Status**: pending / running / passed / failed / skipped / waiting
- **Short human explanation**: What this stage does
- **Start time**: When stage started
- **End time**: When stage completed (if applicable)
- **Duration**: Time taken for stage
- **Key inputs**: What data/config was used
- **Key outputs**: What was produced
- **Metrics**: Relevant metrics for the stage
- **Logs**: Expand/collapse for detailed logs
- **Error**: Failure message if stage failed
- **Suggested next action**: Recommendation if stage failed
- **"Ask AI about this stage" button**: Contextual AI assistance

#### Stage Card Interactions
- Click stage card to expand details
- Hover for quick status summary
- Color-coded status border
- Progress bar for running stages
- Click "Ask AI" to open AI Assistant with stage context

#### Run Controls
- **Pause/Resume** button (if supported)
- **Cancel Run** button (with confirmation)
- **Run Speed** selector (if applicable)
- **Export Current Results** button (if applicable)

## Page 3 — Strategy Lab

### Purpose
Design or inspect strategy ideas before running AutoQuant validation.

### Sections

#### Strategy Idea Prompt
- Large text area for strategy concept
- Placeholder text with examples
- Character count indicator
- "Clear" button

#### Style Selector
- Dropdown or card selection
- Style descriptions on hover
- Filter by direction compatibility

#### Direction Selector
- Long only / Short only / Long and short
- Auto-suggest based on style selection

#### Indicator Family Selector
- Multi-select for indicator categories:
  - Trend indicators (MA, EMA, MACD)
  - Momentum indicators (RSI, Stochastic)
  - Volatility indicators (Bollinger Bands, ATR)
  - Volume indicators (OBV, Volume MA)
- Individual indicator selection within families
- Parameter ranges for each indicator

#### AI-Generated StrategySpec Viewer
- JSON display panel with syntax highlighting
- Validation status indicator
- "Copy to Clipboard" button
- "Download JSON" button

#### StrategySpec JSON Editor
- Code editor with JSON validation
- Real-time syntax checking
- Error display panel
- "Validate" button
- "Reset to AI Generated" button

#### Template Preview
- Strategy template structure display
- Parameter mapping visualization
- "Full Template" button to see complete template

#### Generated Freqtrade Code Preview
- Python code display panel
- Syntax highlighting
- Class structure overview
- "Download .py" button (disabled until approved)

#### Generated .json Params Preview
- Parameter file display panel
- Validation status
- "Download .json" button (disabled until approved)

#### Save Draft Button
- Save current StrategySpec as draft
- Draft name input
- Draft versioning

#### Send to AutoQuant Button
- Navigate to AutoQuant page with current StrategySpec
- Confirmation dialog
- Transfer strategy design to validation workflow

### Rules
- AI Strategy Designer outputs StrategySpec JSON only
- Free-form strategy code generation is not allowed
- Backend templates generate actual strategy files
- User cannot directly edit generated Python code
- All code generation goes through deterministic templates

## Page 4 — Optimizer

### Purpose
Improve parameters for one selected strategy using hyperopt.

### Sections

#### Strategy Selector
- Dropdown to select strategy
- Strategy preview panel
- Current parameters display

#### Pair Selector
- Manual pair input or auto universe
- Pair validation
- Multi-pair selection support

#### Timeframe Selector
- Timeframe dropdown
- Timeframe validation for strategy

#### Timerange Selector
- Date range picker
- Preset options (30d, 90d, 1y)
- Training/validation split display

#### Parameter Mode
Radio buttons:
- **Manual** - User specifies parameter ranges
- **Auto Safe** - System generates safe parameter ranges

#### Parameter Lock Table
Table showing all strategy parameters:
- Parameter name
- Current value
- Lock status (locked/unlocked)
- Min/Max range (if unlocked)
- Step size (if unlocked)
- Lock/unlock toggle

#### Hyperopt Spaces
Checkbox selection for optimization spaces:
- **buy** - Buy signal parameters
- **sell** - Sell signal parameters
- **roi** - ROI exit parameters
- **stoploss** - Stoploss parameters
- **trailing** - Trailing stop parameters
- **protection** - Protection parameters

#### Trials Table
- Trial number
- Parameter values
- Objective function result
- Key metrics (profit, drawdown, trades)
- Status (completed/failed)
- "View Details" button

#### Best Trial Card
- Trial number
- Parameter values
- Objective function score
- Performance metrics
- Comparison to baseline
- "Select Best" button

#### Before/After Metrics
- Side-by-side comparison table
- Baseline vs Optimized metrics
- Percentage change indicators
- Visual improvement/declination indicators

#### Promote Best to Candidate
- "Promote to Candidate" button
- Confirmation dialog
- Creates new run with optimized parameters

#### Export Best Params
- "Export Parameters" button
- Downloads `.json` with optimized parameters
- Option to update strategy file

#### Warning Display
- **Too few trades warning** - If optimized result has insufficient trades
- **Overfitting warning** - If optimization shows overfitting signs
- **Parameter sensitivity warning** - If results are too sensitive

### Rules
- Optimizer does not automatically prove a strategy is profitable
- Best hyperopt result must be validated again with full backtest
- ROI/stoploss/trailing/protection should not be freely changed unless policy allows
- Too many optimized parameters increases overfitting risk
- User must explicitly confirm parameter changes

## Page 5 — Runs

### Purpose
List and open every historical run for review and comparison.

### Sections

#### Runs Table
Main table displaying all historical runs with filters and sorting.

#### Filters
Filter panel with:
- **Status** - Dropdown (all, running, completed, failed, rejected)
- **Strategy** - Text search or dropdown
- **Date range** - Date picker
- **Pair** - Multi-select dropdown
- **Timeframe** - Multi-select dropdown
- **Classification** - Dropdown (all, rejected, candidate, promising, validated, approved)
- **Apply Filters** button
- **Reset Filters** button

#### Table Columns
- **Run ID** - Unique identifier (clickable for details)
- **Run Name** - User-provided name
- **Strategy** - Strategy name (clickable)
- **Status** - Status with color indicator
- **Classification** - Final classification (if applicable)
- **Net Profit** - Profit value with percentage
- **Profit Factor** - PF value
- **Max Drawdown** - Drawdown percentage
- **Trade Count** - Number of trades
- **Created At** - Timestamp
- **Duration** - Run duration
- **Actions** - View, Compare, Delete buttons

#### Table Interactions
- Sort by any column
- Click row to open run details
- Multi-select for comparison
- Pagination for large result sets
- Export table to CSV

#### Run Detail View
Opens when run is clicked:
- Complete run information
- All stage results
- Final classification
- Export options
- Repair options (if failed)
- Compare with other runs option

#### Compare Runs
- Select multiple runs for comparison
- Side-by-side metrics comparison
- Visual charts comparison
- Parameter differences
- Classification comparison

#### Delete/Archive
- Delete with confirmation dialog
- Archive option (move to archive, keep data)
- Bulk actions for multiple runs
- Cannot delete running runs

## Page 6 — Results

### Purpose
Show detailed results for selected run with comprehensive analysis.

### Sections

#### Decision Summary
- Final classification with large status indicator
- Overall decision explanation
- Key metrics summary
- Approval/rejection reasoning

#### Final Classification
- Classification level (Rejected/Candidate/Promising/Validated/Approved)
- Classification criteria checklist
- Passed gates display
- Failed gates display
- Confidence score

#### Why Accepted/Rejected
- Detailed explanation of decision
- Specific reasons for classification
- Comparison to thresholds
- Improvement suggestions (if rejected)

#### Metrics Cards
Grid of key metric cards:

- **Net Profit** - Absolute and percentage profit
- **Profit Factor** - Gross profit/gross loss ratio
- **Max Drawdown** - Maximum peak-to-trough decline
- **Sharpe Ratio** - Risk-adjusted return metric
- **Calmar Ratio** - Return/drawdown ratio
- **Win Rate** - Percentage of winning trades
- **Trade Count** - Total number of trades
- **Expectancy** - Average profit per trade

Each card shows:
- Metric value
- Threshold comparison
- Status indicator (pass/fail)
- Trend indicator (vs baseline or previous run)

#### Equity Curve Chart
- Line chart showing equity over time
- Drawdown overlay
- Reference lines for key levels
- Zoom and pan controls
- Export chart option

#### Drawdown Chart
- Drawdown depth over time
- Maximum drawdown marker
- Drawdown duration periods
- Recovery periods

#### Pair Performance Table
- Pair name
- Net profit per pair
- Trade count per pair
- Win rate per pair
- Profit factor per pair
- Status per pair

#### Trades Table
- Trade number
- Entry time
- Exit time
- Pair
- Direction (long/short)
- Entry price
- Exit price
- Profit/Loss
- Profit/Loss percentage
- Entry reason
- Exit reason
- Duration

Table features:
- Sort and filter
- Pagination
- Export to CSV
- Click for trade details

#### Entry/Exit Reason Analysis
- Entry reason frequency distribution
- Exit reason frequency distribution
- Profitability by entry reason
- Profitability by exit reason
- Chart visualization

#### WFA Results
- Walk-forward analysis summary
- In-sample vs out-of-sample performance
- Window-by-window results table
- Performance consistency chart
- Overfitting assessment

#### OOS Results
- Out-of-sample performance metrics
- OOS vs in-sample comparison
- Performance degradation analysis
- OOS stability assessment

#### Robustness Results
- Multi-pair performance summary
- Parameter sensitivity analysis
- Market regime performance
- Safety check results
- Stability score

#### Hyperopt Comparison
- Baseline vs optimized comparison
- Parameter changes
- Performance differences
- Overfitting risk assessment
- Validation of optimized results

#### Export Buttons
- **Export Strategy** - `.py` and `.json` files
- **Export Report** - PDF or HTML report
- **Export Data** - CSV of all results
- **Export Charts** - Image files of charts

#### Ask AI to Explain Results
- "Ask AI to explain these results" button
- Opens AI Assistant with results context
- Pre-populated question about results
- AI provides detailed explanation

## Page 7 — Strategy Editor

### Purpose
Inspect and safely edit strategy files and parameters with version control.

### Sections

#### Strategy File Tree
- Tree view of strategy directory
- Strategy files (`.py`)
- Parameter files (`.json`)
- Version history (if available)
- Create new file/folder options

#### .py Editor
- Code editor with syntax highlighting
- Freqtrade strategy structure validation
- Error detection and display
- Line numbers
- Search and replace
- Code folding

#### .json Params Editor
- JSON editor with validation
- Parameter type checking
- Range validation
- Schema validation
- Error display

#### Metadata Panel
- Strategy name
- Class name
- Timeframe
- Direction
- Last modified
- Version history
- Associated runs

#### Validation Panel
- Real-time validation status
- Syntax errors
- Import errors
- Parameter errors
- Freqtrade compatibility check
- "Validate" button

#### Diff Viewer
- Compare current version with previous
- Side-by-side diff display
- Line-by-line changes
- Color-coded additions/deletions
- "Accept Changes" / "Reject Changes" buttons

#### Save with Backup
- "Save" button
- Automatic backup creation
- Version comment input
- Backup location display
- "View Backups" button

#### Restore Previous Version
- Version history dropdown
- Version comparison
- "Restore" button with confirmation
- Backup creation before restore

#### Send to AutoQuant
- "Send to AutoQuant" button
- Navigate to AutoQuant page
- Pre-fill configuration
- Start new run with edited strategy

#### Export
- "Export .py" button
- "Export .json" button
- "Export Both" button
- Export location selection

### Rules
- Destructive edits require confirmation dialog
- Accepted strategy overwrites require explicit confirmation
- `.env` is never shown or accessible in Strategy Editor
- Secrets are never displayed in any editor
- Every save creates a version backup automatically
- User cannot edit system files or configuration

## Page 8 — AI Assistant

### Purpose
Interactive chat interface for communicating with AutoQuant's AI assistant.

### Sections

#### Chat Interface
- Message history display
- User message input area
- Send button
- Clear conversation button
- Export conversation button

#### Context Selector
Dropdown to select conversation context:
- **Current run** - Discuss active or selected run
- **Selected strategy** - Discuss specific strategy
- **Selected stage** - Discuss specific validation stage
- **Latest error** - Discuss recent error or failure
- **Results** - Discuss specific results
- **General** - General questions about AutoQuant

#### Suggested Questions
Quick action buttons for common questions:
- **"Why did this fail?"** - Explain failure reason
- **"What should I try next?"** - Get recommendations
- **"Is this overfit?"** - Assess overfitting risk
- **"Explain these metrics"** - Metric explanation
- **"What changed after hyperopt?"** - Hyperopt impact analysis
- **"How can I improve this strategy?"** - Improvement suggestions

#### AI Action Requests
Structured requests for AI assistance:
- **Draft repair** - Generate repair suggestion
- **Draft StrategySpec** - Create strategy specification
- **Explain report** - Explain validation report
- **Prepare Discord summary** - Generate notification message

### Rules
- Read-only by default for all system operations
- Any write/run action requires explicit user confirmation
- AI must cite internal data when discussing results
- AI must not invent metrics or fabricate data
- AI cannot execute commands without approval
- AI cannot modify files without confirmation
- AI cannot access secrets or sensitive data

## Page 9 — Settings

### Purpose
Configure local system components and AutoQuant behavior.

### Sections

#### Freqtrade Settings
- **Freqtrade executable/path** - Path input with browse button
- **user_data directory** - Path input with browse button
- **strategy directory** - Path input with browse button
- **data directory** - Path input with browse button
- **config template** - File selector for base config
- **Test Connection** button
- **Version display** (if connected)

#### Ollama Settings
- **Base URL** - URL input (default: http://localhost:11434)
- **Model** - Model selector dropdown
- **Test Connection** button
- **Available models** list (refresh button)
- **Model parameters** (temperature, etc.)

#### Discord Settings
- **Bot enabled** - Toggle switch
- **Channel ID** - Text input
- **Notification rules** - Checklist of events to notify
- **Test message** button to send test notification
- **Token storage note** - "Token stored only in .env"
- **Status indicator** (connected/disabled)

#### Exchange Settings
- **Exchange name** - Dropdown (Binance, Kraken, etc.)
- **Quote currency** - Dropdown (USDT, BTC, etc.)
- **Default pairs** - Text input (comma-separated)
- **Trading mode** - Radio buttons (spot/futures)
- **API key configuration** (stored in .env only)

#### Risk Profiles
Configurable risk thresholds for each profile:

**Conservative**:
- Max drawdown: 15%
- Profit Factor: 1.5+
- Minimum trades: 100+
- Other conservative thresholds

**Balanced**:
- Max drawdown: 25%
- Profit Factor: 1.3+
- Minimum trades: 50+
- Other balanced thresholds

**Aggressive**:
- Max drawdown: 35%
- Profit Factor: 1.2+
- Minimum trades: 25+
- Other aggressive thresholds

Each profile has:
- Editable threshold fields
- "Reset to defaults" button
- "Save" button

#### Data Settings
- **Auto download enabled** - Toggle switch
- **Default timerange** - Preset selector
- **Data format** - Format selector (json, etc.)
- **Data directory** - Path display
- **Download on demand** - Toggle
- **Data retention policy** - Days/weeks selector

#### Backup Settings
- **Backup path** - Path input with browse button
- **Strategy versioning** - Toggle switch
- **Backup frequency** - Selector (on save, daily, weekly)
- **Retention policy** - Number of backups to keep
- **Backup status** - Last backup time, size

#### Developer Diagnostics
- **Logs** - View system logs
- **Environment status** - Python version, dependencies
- **API health** - Backend API status check
- **Database integrity** - Database check and repair
- **System resources** - CPU, memory, disk usage
- **Export diagnostics** - Download diagnostic report

### Settings Behavior
- Settings persist in local configuration
- Changes require "Save" button
- Validation before saving
- "Reset to defaults" option for each section
- Settings reload not required for most changes
- Some changes may require restart (indicated)

## Run Selector Behavior

### Top Bar Run Selector
- Always shows currently active run (if any)
- Dropdown to select from recent runs
- "No run selected" state when no active run
- Selecting run updates context across pages

### Context Updates
When run is selected:
- **AutoQuant page** - Shows selected run details
- **Results page** - Shows selected run results
- **Strategy Editor** - Shows strategy from selected run
- **AI Assistant** - Context set to selected run

### Empty State Behavior
When no run is selected:
- **AutoQuant page** - Shows run setup interface
- **Results page** - Shows empty state with guidance
- **Strategy Editor** - Shows strategy browser
- **AI Assistant** - Shows general assistance mode

### Run Selection Persistence
- Selected run persists across page navigation
- Selection cleared on explicit "Clear Selection" action
- Selection remembered within session

## AI Assistant Drawer

### Drawer Behavior
- Slides in from right side when activated
- Can be opened from any page
- Context-aware based on current page
- Collapsible to minimize screen space
- Close button to dismiss

### Context Awareness
- **Dashboard** - General system questions
- **AutoQuant** - Current run and stage questions
- **Strategy Lab** - Strategy design questions
- **Optimizer** - Parameter optimization questions
- **Runs** - Historical run analysis
- **Results** - Result interpretation
- **Strategy Editor** - Code and parameter questions
- **Settings** - Configuration assistance

### Quick Actions
- "Ask about current page" button
- "Explain what I'm seeing" button
- "Suggest next action" button
- Context-specific suggestions based on page

## Responsive Design

### Desktop (> 1200px)
- Full sidebar navigation
- All page sections visible
- AI Assistant drawer available
- Multi-column layouts

### Tablet (768px - 1200px)
- Collapsible sidebar
- Optimized layouts
- AI Assistant drawer available
- Vertical stacking where needed

### Mobile (< 768px)
- Bottom navigation or hamburger menu
- Single column layouts
- Simplified views
- AI Assistant as overlay
- Critical information prioritized

## Accessibility

### Keyboard Navigation
- Full keyboard navigation support
- Focus indicators
- Keyboard shortcuts for common actions
- Skip to main content option

### Screen Reader Support
- ARIA labels on interactive elements
- Semantic HTML structure
- Alt text on images and charts
- Screen reader-compatible status updates

### Color Contrast
- WCAG AA compliant color contrast
- Status colors with text indicators
- Color-blind friendly status indicators

### Error Handling
- Clear error messages
- Error recovery guidance
- Form validation with specific error locations
- Graceful degradation for missing features

## Performance

### Loading States
- Skeleton screens for content loading
- Progress indicators for long operations
- Optimistic UI updates where appropriate
- Loading timeouts with error handling

### Real-time Updates
- WebSocket connection for live run updates
- Efficient update batching
- Throttled refresh rates
- Connection status indicators

### Data Caching
- Local storage for preferences
- Cached API responses where appropriate
- Cache invalidation strategy
- Offline capability for read-only views

## Summary

The AutoQuant UI provides a comprehensive, modern interface for local strategy validation. The design prioritizes clarity, understandability, and user control throughout the validation lifecycle. Every stage is visible and explainable without requiring raw log analysis. The interface supports the complete workflow from strategy idea to validated export, with AI assistance available at every step. Dark mode, clean cards, and consistent status colors create a professional trading dashboard experience.
