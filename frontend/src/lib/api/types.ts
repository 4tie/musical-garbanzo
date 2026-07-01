export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue>;
export type JsonObject = Record<string, unknown>;

export type ApiErrorKind =
  | 'network'
  | 'timeout'
  | 'http'
  | 'not_found'
  | 'controlled_failure'
  | 'empty_data'
  | 'invalid_response'
  | 'rejected_strategy'
  | 'pipeline_rejected'
  | 'strategy_not_ready';

export interface ApiError {
  kind: ApiErrorKind;
  message: string;
  status?: number;
  detail?: unknown;
  endpoint?: string;
}

export type ApiResult<T> =
  | { success: true; data: T; status: number; empty: boolean }
  | { success: false; error: ApiError; status?: number; empty?: boolean };

export type ApiResponse<T> = ApiResult<T>;

export type SystemHealth = 'healthy' | 'unknown' | 'configured' | 'missing' | 'disabled';

export interface HealthResponse {
  status: string;
  app: string;
  environment: string;
  backend: string;
}

export interface SystemStatusResponse {
  backend: SystemHealth;
  database: SystemHealth;
  freqtrade: SystemHealth;
  ollama: SystemHealth;
  discord: SystemHealth;
  project_root: string;
  freqtrade_user_data_dir: string;
  frontend_port: number;
  backend_port: number;
}

export interface PublicSettingsResponse {
  app_name: string;
  app_env: string;
  backend_port: number;
  frontend_port: number;
  freqtrade_user_data_dir: string;
  freqtrade_config_dir: string;
  ollama_base_url: string;
  ollama_model_configured: boolean;
  discord_enabled: boolean;
  discord_channel_configured: boolean;
  database_url: string;
}

export type UiStatus =
  | 'system_failed'
  | 'pipeline_completed'
  | 'strategy_rejected'
  | 'optimization_rejected'
  | 'controlled_failure'
  | 'pending'
  | 'running';

export interface RunListItem {
  id: string;
  name: string;
  mode: string;
  status: string;
  classification: string | null;
  strategy_id: string | null;
  parent_run_id: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface RunRead extends RunListItem {
  exchange: string | null;
  quote_currency: string | null;
  trading_mode: string | null;
  timeframe: string | null;
  pairs: string[] | null;
  timerange: string | null;
  risk_profile: string | null;
  analysis_depth: string | null;
  failure_reason: string | null;
}

export interface RunStageRead {
  id: string;
  run_id: string;
  stage_key: string;
  stage_name: string;
  order_index: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  input: unknown;
  output: unknown;
  error: unknown;
  logs_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface BaselineStageResult {
  stage_name: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  message?: string | null;
  error_code?: string | null;
  warnings?: string[];
  errors?: string[];
  artifact_paths?: string[];
  details?: JsonObject;
}

export interface BaselineRunDetail {
  run_id: string;
  status: string;
  classification: string | null;
  confidence_score?: number | null;
  mode?: string;
  created_at?: string | null;
  updated_at?: string | null;
  stages: BaselineStageResult[];
  metrics: JsonObject;
  decision: JsonObject;
  artifacts: string[];
  warnings: string[];
  errors: string[];
}

export interface BaselineStatusResponse {
  run_id: string;
  status: string;
  classification: string | null;
  current_stage: string | null;
  stage_results: BaselineStageResult[];
  metrics: JsonObject;
  decision: JsonObject;
  warnings: string[];
  errors: string[];
}

export interface BaselineReport {
  run_id: string;
  artifact_id: string;
  artifact_type: string;
  description: string | null;
  file_path: string;
  sha256: string | null;
  size_bytes: number | null;
  created_at: string | null;
}

export interface OptimizationRunListItem {
  id: string;
  strategy_name: string;
  timeframe: string;
  pairs: string[];
  exchange: string;
  status: string;
  result_status: string | null;
  epochs_requested: number | null;
  epochs_completed: number | null;
  best_trial_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OptimizationRun extends OptimizationRunListItem {
  parent_run_id: string | null;
  baseline_run_id: string | null;
  optimized_run_id: string | null;
  risk_profile: string | null;
  spaces: string[] | null;
  policy: JsonObject | null;
  request: JsonObject | null;
  comparison: JsonObject | null;
  report_artifact_path: string | null;
}

export interface OptimizationTrial {
  id: string;
  optimization_run_id: string;
  trial_number: number;
  status: string;
  is_best: boolean;
  is_selected_for_validation: boolean;
  params: JsonObject;
  buy_params: JsonObject | null;
  sell_params: JsonObject | null;
  roi_params: JsonObject | null;
  stoploss_params: JsonObject | null;
  trailing_params: JsonObject | null;
  metrics: JsonObject | null;
  loss_score: number | null;
  profit_total: number | null;
  profit_factor: number | null;
  expectancy: number | null;
  max_drawdown: number | null;
  trade_count: number | null;
  win_rate: number | null;
  rejection_reason: string | null;
  failure_reason: string | null;
  artifact_paths: string[];
  raw_trial: JsonObject | null;
  created_at: string;
}

export interface OptimizationComparison {
  optimization_run_id: string;
  baseline_run_id: string | null;
  optimized_run_id: string | null;
  best_trial_id: string | null;
  baseline_metrics: JsonObject | null;
  optimized_metrics: JsonObject | null;
  delta_profit_factor: number | null;
  delta_expectancy: number | null;
  delta_drawdown: number | null;
  delta_trade_count: number | null;
  baseline_classification: string | null;
  optimized_classification: string | null;
  result_status: string | null;
  improvement_summary: string | null;
  warnings: string[];
  overfit_suspected: boolean;
  created_at: string | null;
}

export interface OptimizationRunDetail {
  run: OptimizationRun;
  stages: BaselineStageResult[];
  best_trial: OptimizationTrial | null;
  comparison: OptimizationComparison | null;
  artifact_paths: string[];
}

export interface OptimizationStatusResponse {
  run_id: string;
  status: string;
  current_stage: string | null;
  stage_progress: JsonObject | null;
  epochs_completed: number | null;
  epochs_total: number | null;
  trials_completed: number | null;
  trials_total: number | null;
  message: string | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface OptimizationTrialDetail {
  trial: OptimizationTrial;
  artifact_paths: string[];
}

export interface OptimizationReport {
  optimization_run_id: string;
  report_artifact_path: string;
  status: string;
  report: JsonObject;
}

export interface MetricSnapshot {
  id: string;
  run_id: string;
  stage_key: string | null;
  net_profit: number | null;
  profit_factor: number | null;
  max_drawdown: number | null;
  sharpe: number | null;
  calmar: number | null;
  win_rate: number | null;
  trade_count: number | null;
  expectancy: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  raw_json: JsonObject | null;
  created_at: string;
}

export interface PairResult {
  id: string;
  run_id: string;
  pair: string;
  net_profit: number | null;
  profit_factor: number | null;
  max_drawdown: number | null;
  trade_count: number | null;
  win_rate: number | null;
  expectancy: number | null;
  raw_json: JsonObject | null;
  created_at: string;
}

export interface TradeSummary {
  id: string;
  run_id: string;
  total_trades: number | null;
  wins: number | null;
  losses: number | null;
  draws: number | null;
  avg_duration: string | null;
  best_pair: string | null;
  worst_pair: string | null;
  raw_json: JsonObject | null;
  created_at: string;
}

export interface ResultQualityFlag {
  code: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  details?: JsonObject | null;
}

export interface ResultQualityReport {
  run_id: string | null;
  parse_quality: string;
  flags: ResultQualityFlag[];
  warnings: string[];
  errors: string[];
  is_usable_for_metrics: boolean;
  is_usable_for_decision: boolean;
}

export interface BacktestCombinedResult {
  run_id: string;
  latest_metrics: JsonObject | null;
  pair_results: JsonObject[];
  trade_summary: JsonObject | null;
  quality_report: ResultQualityReport | null;
  normalized_result_path: string | null;
  warnings: string[];
}

export interface ArtifactListItem {
  id: string;
  run_id: string | null;
  strategy_id: string | null;
  artifact_type: string;
  file_path: string;
  description: string | null;
  created_at: string;
}

export interface ArtifactRead extends ArtifactListItem {
  sha256: string | null;
  size_bytes: number | null;
}

export type StrategyReadiness =
  | 'ready'
  | 'warning'
  | 'missing_sidecar'
  | 'invalid'
  | 'parse_error'
  | 'unsafe';

export type StrategyIssueSeverity = 'info' | 'warning' | 'error' | 'critical';

export interface StrategyIssue {
  code: string;
  severity: StrategyIssueSeverity;
  message: string;
  details: JsonObject;
}

export interface StrategyParamsSummary {
  strategy_name: string;
  sidecar_json_path: string | null;
  exists: boolean;
  parse_success: boolean;
  sections_present: string[];
  section_counts: Record<string, number>;
  timeframe: string | null;
  max_open_trades: number | null;
  preview: JsonObject;
  issues: StrategyIssue[];
  warnings: string[];
}

export interface StrategySummary {
  strategy_name: string;
  strategy_file_path: string;
  sidecar_json_path: string | null;
  has_sidecar: boolean;
  readiness: StrategyReadiness;
  issues: StrategyIssue[];
  warnings: string[];
  metadata: JsonObject;
  params_summary: StrategyParamsSummary;
  updated_at: string | null;
}

export interface StrategyDetail extends StrategySummary {
  class_name: string | null;
  file_name: string;
  apparent_strategy_name: string;
  syntax_valid: boolean;
  static_checks: Record<string, boolean>;
}

export interface StrategyImportRequest {
  source_path: string;
  sidecar_source_path?: string | null;
  strategy_name?: string | null;
  overwrite_confirmed?: boolean;
}

export interface StrategyImportResult {
  success: boolean;
  imported: boolean;
  conflict: boolean;
  strategy_name: string | null;
  strategy_file_path: string | null;
  sidecar_json_path: string | null;
  readiness: StrategyReadiness | null;
  issues: StrategyIssue[];
  warnings: string[];
  existing_files: Record<string, string>;
  detail: StrategyDetail | null;
}

export type UiStrategyStatusTone = 'success' | 'warning' | 'danger' | 'neutral';

export interface UiStrategyStatus {
  readiness: StrategyReadiness;
  label: string;
  tone: UiStrategyStatusTone;
  selectableForRun: boolean;
}

export interface UiStrategyRow {
  name: string;
  strategyFilePath: string;
  sidecarJsonPath: string | null;
  hasSidecar: boolean;
  readiness: StrategyReadiness;
  status: UiStrategyStatus;
  issueCount: number;
  warningCount: number;
  sectionsPresent: string[];
  timeframe: string | null;
  canShort: boolean | null;
  updatedAt: string | null;
  raw: StrategySummary;
}

export interface RunLog {
  id: string;
  run_id: string;
  level: string;
  source: string;
  message: string;
  stage_key: string | null;
  details: JsonObject | null;
  created_at: string;
}

export interface RetryHistoryItem {
  id: string;
  run_id: string;
  parent_run_id: string | null;
  attempt_number: number;
  reason: string | null;
  stage_key: string | null;
  status: string;
  error_message: string | null;
  proposed_fix: JsonObject | null;
  applied_fix: JsonObject | null;
  created_at: string;
  completed_at: string | null;
}

export interface AuditLog {
  id: string;
  run_id: string | null;
  actor: string;
  action_type: string;
  description: string | null;
  target_type: string | null;
  target_id: string | null;
  before: JsonObject | null;
  after: JsonObject | null;
  changed_files: unknown[] | null;
  rollback_path: string | null;
  approved: boolean;
  notes: string | null;
  created_at: string;
}

export interface DecisionPolicySummary {
  name: string;
  description: string;
  risk_profile: string;
  thresholds?: JsonObject;
}

export type DecisionRecord = JsonObject;

export interface UiRunListItem {
  id: string;
  label: string;
  mode: string;
  status: string;
  uiStatus: UiStatus;
  classification: string | null;
  strategyId: string | null;
  parentRunId: string | null;
  createdAt: string;
  updatedAt: string;
  startedAt: string | null;
  completedAt: string | null;
}

export interface UiTimelineStage {
  id: string;
  key: string;
  name: string;
  order: number;
  status: string;
  uiStatus: UiStatus;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  message: string | null;
  errorCode: string | null;
  warnings: string[];
  errors: string[];
  details: unknown;
}

export interface UiMetricCard {
  key: string;
  label: string;
  value: number | string | null;
  unit?: string;
  tone: 'neutral' | 'good' | 'warning' | 'danger';
  source?: string;
}

export interface UiTrialRow {
  id: string;
  trialNumber: number;
  status: string;
  uiStatus: UiStatus;
  isBest: boolean;
  isSelectedForValidation: boolean;
  lossScore: number | null;
  profitTotal: number | null;
  profitFactor: number | null;
  expectancy: number | null;
  maxDrawdown: number | null;
  tradeCount: number | null;
  winRate: number | null;
  rejectionReason: string | null;
  failureReason: string | null;
  createdAt: string;
}

export interface UiComparisonRow {
  metric: string;
  baseline: unknown;
  optimized: unknown;
  delta: unknown;
  tone: 'neutral' | 'good' | 'warning' | 'danger';
}

export interface UiArtifactLink {
  id: string;
  label: string;
  type: string;
  path: string;
  description: string | null;
  createdAt: string | null;
  runId?: string | null;
  strategyId?: string | null;
}

export type UnifiedRunType = 'baseline' | 'optimization';

// Request schemas for Part 10 safe run controls
export interface BaselineEvaluationRequest {
  strategy_name: string;
  pairs: string[];
  timeframe: string;
  exchange?: string;
  days?: number;
  timerange?: string;
  risk_profile?: string;
  stake_currency?: string;
  stake_amount?: number | string;
  max_open_trades?: number;
  trading_mode?: string;
  download_missing_data?: boolean;
  user_confirmed: boolean;
  apply_decision_to_run?: boolean;
  force_parse?: boolean;
  notes?: string;
}

export interface BaselineEvaluationResult {
  success: boolean;
  run_id: string | null;
  status: string;
  classification: string | null;
  confidence_score: number | null;
  strategy_name: string;
  pairs: string[];
  timeframe: string;
  exchange: string;
  risk_profile: string;
  metrics: JsonObject;
  decision: JsonObject;
  quality_flags: string[];
  stage_results: BaselineStageResult[];
  artifact_paths: string[];
  warnings: string[];
  errors: string[];
  next_actions: string[];
}

export interface OptimizationRequest {
  strategy_name: string;
  pairs: string[];
  timeframe: string;
  exchange?: string;
  days?: number;
  timerange?: string;
  risk_profile?: string;
  baseline_run_id?: string;
  run_baseline_first?: boolean;
  /** Always sent as true — data download is now automatic when user_confirmed=true */
  download_missing_data?: boolean;
  user_confirmed: boolean;
  epochs?: number;
  spaces?: string[];
  max_open_trades?: number;
  stake_currency?: string;
  stake_amount?: number | string;
  apply_decision_to_run?: boolean;
  /** Stored in request_json blob on the backend via the 'notes' field */
  notes?: string;
}

export interface AvailablePairsResponse {
  pairs: string[];
  count: number;
  total_available: number;
  exchange: string;
  quote: string;
  source: string;
  available: boolean;
  message: string;
  error?: string;
}

export interface SupportedExchange {
  id: string;
  name: string;
  note: string;
}

export interface OptimizationStartResponse {
  run_id: string;
  status: string;
  message: string;
  errors?: string[];
  warnings?: string[];
  next_actions?: string[];
}

export interface UnifiedRunRow {
  id: string;
  type: UnifiedRunType;
  detailHref: string;
  strategyName: string | null;
  pairs: string[];
  timeframe: string | null;
  status: string;
  uiStatus: UiStatus;
  classification: string | null;
  resultStatus: string | null;
  trialsCount: number | null;
  bestTrialId: string | null;
  createdAt: string;
  updatedAt: string;
  searchText: string;
}

// Validation types
export interface ValidationRunRequest {
  source_type: string;
  source_run_id?: string;
  strategy_name: string;
  pairs: string[];
  timeframe: string;
  exchange?: string;
  risk_profile?: string;
  timerange?: string;
  days?: number;
  oos_ratio?: number;
  wfo_enabled?: boolean;
  wfo_train_days?: number;
  wfo_test_days?: number;
  wfo_step_days?: number;
  wfo_max_windows?: number;
  robustness_enabled?: boolean;
  sensitivity_enabled?: boolean;
  download_missing_data?: boolean;
  user_confirmed: boolean;
  notes?: string;
}

export interface ValidationRunResponse {
  validation_run_id: string;
  status: string;
  decision_status?: string;
  strategy_name: string;
  pairs: string[];
  timeframe: string;
  exchange: string;
  risk_profile?: string;
  warnings: string[];
  errors: string[];
  next_actions: string[];
}

export interface ValidationRunListItem {
  validation_run_id: string;
  strategy_name: string;
  source_type: string;
  source_run_id?: string;
  pairs: string[];
  timeframe: string;
  status: string;
  decision_status?: string;
  created_at: string;
  updated_at: string;
  summary?: {
    decision_status?: string;
    evidence_count?: number;
    warnings?: string[];
    errors?: string[];
    next_actions?: string[];
  };
}

export interface ValidationRunDetail {
  run: {
    validation_run_id: string;
    source_type: string;
    source_run_id?: string;
    strategy_name: string;
    pairs: string[];
    timeframe: string;
    exchange?: string;
    risk_profile?: string;
    status: string;
    decision_status?: string;
    timerange?: string;
    oos_timerange?: string;
    created_at: string;
    updated_at: string;
  };
  request?: ValidationRunRequest;
  candidate_reference?: Record<string, unknown>;
  oos_summary?: ValidationEvidence;
  wfo_summary?: ValidationEvidence;
  robustness_summary?: {
    checks: ValidationEvidence[];
    count: number;
  };
  sensitivity_summary?: {
    checks: ValidationEvidence[];
    count: number;
  };
  final_decision?: ValidationDecision;
  report_path?: string;
  evidence: ValidationEvidence[];
  warnings: string[];
  errors: string[];
  next_actions: string[];
  summary?: Record<string, unknown>;
}

export interface ValidationStatusResponse {
  validation_run_id: string;
  status: string;
  decision_status?: string;
  current_stage?: string;
  evidence_count: number;
  message?: string;
  completed_stages: string[];
  failed_stage?: string;
  summary?: Record<string, unknown>;
  warnings: string[];
  errors: string[];
  created_at: string;
  updated_at: string;
}

export interface ValidationEvidenceResponse {
  validation_run_id: string;
  evidence: ValidationEvidence[];
  oos: ValidationEvidence[];
  wfo_windows: ValidationEvidence[];
  wfo_summary: ValidationEvidence[];
  robustness: ValidationEvidence[];
  sensitivity: ValidationEvidence[];
}

export interface ValidationReportResponse {
  validation_run_id: string;
  report_artifact_path: string;
  report: Record<string, unknown>;
}

export interface ValidationEvidence {
  id?: string;
  validation_run_id: string;
  evidence_type: string;
  status: string;
  window_index?: number;
  timerange?: string;
  metrics: Record<string, unknown>;
  decision: Record<string, unknown>;
  issues: ValidationIssue[];
  warnings: string[];
  artifact_paths: string[];
  created_at?: string;
  check_name?: string;
}

export interface ValidationIssue {
  code: string;
  message: string;
  severity: string;
  details: Record<string, unknown>;
}

export interface ValidationDecision {
  decision_status: string;
  confidence_score?: number;
  policy_name?: string;
  reasons: string[];
  blocking_failures: string[];
  warnings: string[];
  next_actions: string[];
}
