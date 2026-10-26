export type NovaState = 
  | "IDLE" 
  | "LISTENING" 
  | "THINKING" 
  | "EXECUTING" 
  | "SPEAKING" 
  | "ERROR";

export interface CpuTelemetry {
  percent: number;
  core_count: number;
  physical_cores: number;
}

export interface RamTelemetry {
  percent: number;
  used_gb: number;
  total_gb: number;
  available_gb: number;
}

export interface DiskTelemetry {
  percent: number;
  used_gb: number;
  total_gb: number;
}

export interface BatteryTelemetry {
  has_battery: boolean;
  percent: number;
  is_plugged: boolean;
  status: string;
}

export interface SystemInfoTelemetry {
  os: string;
  release: string;
  machine: string;
  node: string;
  uptime_hours: number;
}

export interface TelemetryData {
  cpu: CpuTelemetry;
  ram: RamTelemetry;
  disk: DiskTelemetry;
  battery: BatteryTelemetry;
  system: SystemInfoTelemetry;
}

export interface SystemStatusResponse {
  status: string;
  telemetry: TelemetryData;
  assistant: {
    state: NovaState;
    status_message: string;
    timestamp: string;
  };
  memory: {
    total_messages: number;
    session_turns: number;
    db_path: string;
  };
}

export interface AiStatusResponse {
  online: boolean;
  provider: string;
  endpoint: string;
  available_models: string[];
  active_model: string;
  model_ready: boolean;
  message: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  model?: string;
}

export interface ActivityEvent {
  timestamp: string;
  title: string;
  category: "AI" | "SYSTEM" | "CONVERSATION" | "TASK" | string;
  detail: string;
  level: "INFO" | "WARN" | "LIVE" | "SUCCESS" | "ERROR" | string;
}

// Voice Intelligence v0.2 Types
export interface AudioDevice {
  id: number;
  name: string;
  hostapi?: number;
  hostapi_name?: string;
  max_inputs?: number;
  max_outputs?: number;
  default_samplerate?: number;
  is_default_input?: boolean;
  is_default_output?: boolean;
}

export interface VoiceStatusResponse {
  running: boolean;
  pipeline_mode: string;
  wake_word_enabled: boolean;
  wake_word: {
    initialized: boolean;
    active_model_key: string;
    wake_phrase: string;
    is_custom_model: boolean;
    threshold: number;
    error?: string;
    note?: string;
  };
  speech_recognition: {
    initialized: boolean;
    engine: string;
    model_path: string;
    sample_rate: number;
    silence_timeout: number;
    max_timeout: number;
    initial_silence_timeout?: number;
    energy_threshold?: number;
    error?: string;
    last_telemetry?: any;
  };
  tts: {
    initialized: boolean;
    engine: string;
    model_path: string;
    is_speaking: boolean;
    speech_rate: number;
    volume: number;
    output_device?: number;
    error?: string;
  };
  audio: {
    sample_rate: number;
    input_device?: number;
    selected_device_name?: string;
    output_device?: number;
    frames_captured?: number;
    bytes_captured?: number;
    is_muted?: boolean;
    volume_scalar?: number;
  };
}

// Memory Intelligence v0.3 Types
export type MemoryCategory = 
  | "user_profile" 
  | "project" 
  | "conversation" 
  | "task" 
  | "knowledge";

export interface MemoryItem {
  id: string;
  category: MemoryCategory;
  content: string;
  project_id?: string | null;
  confidence: number;
  source: string;
  tags: string[];
  metadata: Record<string, any>;
  access_count: number;
  created_at: string;
  updated_at: string;
  last_accessed_at?: string | null;
}

export interface ProjectItem {
  id: string;
  name: string;
  description: string;
  tech_stack: string[];
  status: string;
  important_decisions: string[];
  known_issues: string[];
  pending_tasks: string[];
  recent_updates: string[];
  created_at: string;
  updated_at: string;
}

export interface ConversationSummaryItem {
  id: string;
  session_id: string;
  summary: string;
  key_points: string[];
  decisions: string[];
  message_count: number;
  start_timestamp?: string | null;
  end_timestamp?: string | null;
  created_at: string;
}

export interface MemoryStatsResponse {
  total_memories: number;
  categories: Record<string, number>;
  total_projects: number;
  total_summaries: number;
  total_tasks: number;
  embedding_model: string;
  device: string;
  status: string;
}

export interface MemorySearchResponse {
  query: string;
  total_found: number;
  results: Array<{
    memory: MemoryItem;
    similarity: number;
  }>;
}

// =========================================================================
// Operational Tools & Execution v0.4 Types
// =========================================================================

export type PermissionLevel = 
  | "READ_ONLY" 
  | "LOW_RISK" 
  | "CONFIRMATION_REQUIRED" 
  | "BLOCKED";

export type ToolCategory = 
  | "APPLICATION" 
  | "FILE_SYSTEM" 
  | "SYSTEM_CONTROL" 
  | "BROWSER";

export type TaskStatus = 
  | "PLANNING" 
  | "PENDING_APPROVAL" 
  | "EXECUTING" 
  | "COMPLETED" 
  | "FAILED" 
  | "CANCELLED" 
  | "REJECTED";

export type StepStatus = 
  | "PENDING" 
  | "RUNNING" 
  | "COMPLETED" 
  | "FAILED" 
  | "SKIPPED" 
  | "CANCELLED";

export interface ToolParameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: any;
  enum_values?: string[];
}

export interface ToolDefinition {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  permission_level: PermissionLevel;
  timeout_seconds: number;
  parameters: ToolParameter[];
  is_reversible: boolean;
}

export interface TaskStep {
  step_id: number;
  tool_id: string;
  description: string;
  arguments: Record<string, any>;
  permission_level: PermissionLevel;
  status: StepStatus;
  result?: Record<string, any>;
  error?: string;
  execution_id?: string;
  started_at?: string;
  completed_at?: string;
}

export interface TaskPlan {
  task_id: string;
  prompt: string;
  description: string;
  steps: TaskStep[];
  status: TaskStatus;
  requires_confirmation: boolean;
  confirmation_reason?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  total_steps: number;
  current_step: number;
  rollback_eligible: boolean;
}

export interface ExecutionRecord {
  id?: number;
  execution_id: string;
  task_id?: string;
  step_id?: number;
  tool_id: string;
  tool_name: string;
  category: string;
  permission_level: string;
  arguments: Record<string, any>;
  status: string;
  result?: Record<string, any>;
  error_message?: string;
  is_reversible: boolean;
  is_rolled_back: boolean;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

// ==========================================
// Vision Intelligence v0.5 Types
// ==========================================

export type CaptureTarget = "PRIMARY" | "ACTIVE_WINDOW" | "ALL_MONITORS" | "MONITOR_INDEX";
export type ImageFormat = "PNG" | "JPEG";
export type VisionMode = "OCR_ONLY" | "MULTIMODAL_VLM" | "HYBRID";
export type RetentionPolicy = "EPHEMERAL" | "SESSION" | "PERSISTENT";

export interface MonitorInfo {
  index: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  is_primary: boolean;
  scale_factor: number;
}

export interface WindowInfo {
  handle: number;
  title: string;
  process_name: string;
  app_name: string;
  left: number;
  top: number;
  width: number;
  height: number;
  is_active: boolean;
  is_minimized: boolean;
  is_sensitive: boolean;
}

export interface CaptureMetadata {
  capture_id: string;
  timestamp: string;
  target: CaptureTarget;
  format: ImageFormat;
  width: number;
  height: number;
  original_width: number;
  original_height: number;
  file_path?: string;
  file_size_bytes: number;
  window_info?: WindowInfo;
  monitor_info?: MonitorInfo;
  base64_preview?: string;
}

export interface OcrWord {
  text: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface OcrLine {
  text: string;
  confidence: number;
  words: OcrWord[];
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface OcrRegion {
  region_id: number;
  lines: OcrLine[];
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface OcrResult {
  total_lines: number;
  total_words: number;
  full_text: string;
  structured_text: string;
  lines: OcrLine[];
  regions: OcrRegion[];
  confidence: number;
  redacted_count: number;
  duration_ms: number;
}

export interface VisionSettings {
  enabled: boolean;
  retention_policy: RetentionPolicy;
  auto_redact_sensitive: boolean;
  exclude_sensitive_windows: boolean;
  default_monitor: number;
  max_image_dimension: number;
  jpeg_quality: number;
  vision_model_name?: string;
  ocr_engine: string;
}

export interface VisionStatus {
  supported: boolean;
  active_engine: string;
  vision_model_available: boolean;
  vision_model_name?: string;
  monitors_count: number;
  active_window?: WindowInfo;
  temporary_captures_count: number;
  settings: VisionSettings;
}

export interface VisualAnalysisRequest {
  prompt: string;
  capture_target?: CaptureTarget;
  monitor_index?: number;
  use_existing_capture_id?: string;
  project_id?: string;
  include_ocr?: boolean;
}

export interface VisualAnalysisResponse {
  answer: string;
  capture_metadata?: CaptureMetadata;
  ocr_result?: OcrResult;
  active_window?: WindowInfo;
  project_context?: string;
  duration_ms: number;
  model_used: string;
  vision_mode: VisionMode;
}

// Agentic Workflows v0.6 Types
export type AgentRole = "researcher" | "developer" | "system" | "vision" | "memory";

export type AgentOperationalStatus = "idle" | "busy" | "waiting_approval" | "error" | "offline";

export interface AgentMetadata {
  role: AgentRole;
  name: string;
  description: string;
  capabilities: string[];
  status: AgentOperationalStatus;
  allowed_tools: string[];
}

export type WorkflowStatus = 
  | "draft" 
  | "planned" 
  | "running" 
  | "waiting_approval" 
  | "completed" 
  | "failed" 
  | "cancelled";

export type WorkflowStepStatus = 
  | "pending" 
  | "ready" 
  | "in_progress" 
  | "waiting_approval" 
  | "completed" 
  | "failed" 
  | "skipped" 
  | "cancelled";

export type WorkflowEventType = 
  | "workflow_started"
  | "step_started"
  | "step_completed"
  | "step_failed"
  | "step_waiting_approval"
  | "step_approved"
  | "step_rejected"
  | "workflow_completed"
  | "workflow_failed"
  | "workflow_cancelled"
  | "workflow_resumed"
  | "agent_message"
  | "reflection_completed";

export interface WorkflowStep {
  step_id: number;
  description: string;
  assigned_agent: AgentRole;
  required_tool?: string;
  input_arguments: Record<string, any>;
  dependencies: number[];
  permission_level: PermissionLevel;
  expected_output?: string;
  timeout_seconds: number;
  max_retries: number;
  retry_count: number;
  status: WorkflowStepStatus;
  result?: Record<string, any>;
  error?: string;
  requires_approval: boolean;
  execution_time_ms?: number;
}

export interface WorkflowPlan {
  workflow_id: string;
  objective: string;
  steps: WorkflowStep[];
  status: WorkflowStatus;
  project_id?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  current_step_id?: number;
}

export interface WorkflowEvent {
  event_id: string;
  workflow_id: string;
  step_id?: number;
  event_type: WorkflowEventType;
  agent_role?: AgentRole;
  message: string;
  timestamp: string;
  payload: Record<string, any>;
}

export interface ReflectionEvaluation {
  step_id: number;
  objective_satisfied: boolean;
  evidence: string;
  missing_information?: string;
  should_continue: boolean;
  human_clarification_required: boolean;
  notes?: string;
}

export interface WorkflowReport {
  workflow_id: string;
  objective: string;
  status: WorkflowStatus;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  duration_seconds: number;
  evidence_summary: string[];
  technical_findings: string;
  unresolved_issues: string[];
  next_steps: string[];
  created_at: string;
}

export interface WorkflowSummary {
  workflow_id: string;
  objective: string;
  status: WorkflowStatus;
  step_count: number;
  created_at: string;
  completed_at?: string;
  summary_text?: string;
}

// ==================== v0.7 PROACTIVE AUTOMATION TYPES ====================

export type AutonomyLevel =
  | "OBSERVE"
  | "PREPARE"
  | "EXECUTE_LOW_RISK"
  | "REQUIRES_APPROVAL"
  | "BLOCKED";

export type TriggerType =
  | "SCHEDULE"
  | "APP_EVENT"
  | "PROJECT_HEALTH"
  | "SYSTEM_THRESHOLD"
  | "WORKFLOW_EVENT"
  | "TASK_OVERDUE"
  | "MANUAL";

export type ScheduleType = "ONCE" | "DAILY" | "WEEKLY" | "RECURRING" | "CRON";

export type AutomationStatus = "ACTIVE" | "PAUSED" | "DISABLED";

export type AutomationActionType =
  | "WORKFLOW"
  | "DAILY_BRIEFING"
  | "PROJECT_HEALTH"
  | "REMINDER"
  | "NOTIFICATION";

export type NotificationType =
  | "REMINDER"
  | "DAILY_BRIEFING"
  | "PROJECT_HEALTH_REPORT"
  | "WORKFLOW_COMPLETED"
  | "WORKFLOW_FAILED"
  | "AUTOMATION_PAUSED"
  | "APPROVAL_REQUIRED";

export interface RetryPolicy {
  max_retries: number;
  retry_delay_seconds: number;
  stop_on_critical: boolean;
}

export interface ScheduleConfig {
  schedule_type: ScheduleType;
  time_of_day?: string;
  days_of_week?: number[];
  interval_seconds?: number;
  specific_datetime?: string;
  cron_expression?: string;
  timezone: string;
}

export interface TriggerConfig {
  trigger_type: TriggerType;
  schedule?: ScheduleConfig;
  app_name?: string;
  app_action?: string;
  system_metric?: string;
  metric_threshold?: number;
  metric_operator?: string;
  workflow_id_pattern?: string;
  workflow_outcome?: string;
  project_id?: string;
  task_filter?: string;
}

export interface AutomationRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  status: AutomationStatus;
  autonomy_level: AutonomyLevel;
  trigger_config: TriggerConfig;
  action_type: AutomationActionType;
  workflow_objective?: string;
  action_payload: Record<string, any>;
  retry_policy: RetryPolicy;
  last_run_at?: string;
  next_run_at?: string;
  run_count: number;
  failure_count: number;
  created_at: string;
  updated_at: string;
}

export interface AutomationCreate {
  id?: string;
  name: string;
  description?: string;
  enabled?: boolean;
  autonomy_level?: AutonomyLevel;
  trigger_config: TriggerConfig;
  action_type?: AutomationActionType;
  workflow_objective?: string;
  action_payload?: Record<string, any>;
  retry_policy?: RetryPolicy;
}

export interface AutomationUpdate {
  name?: string;
  description?: string;
  enabled?: boolean;
  status?: AutomationStatus;
  autonomy_level?: AutonomyLevel;
  trigger_config?: TriggerConfig;
  action_type?: AutomationActionType;
  workflow_objective?: string;
  action_payload?: Record<string, any>;
  retry_policy?: RetryPolicy;
}

export interface AutomationHistoryRecord {
  id: number;
  automation_id: string;
  trigger_type: string;
  action_type: string;
  status: string;
  started_at: string;
  completed_at?: string;
  result_summary?: string;
  error_message?: string;
  workflow_id?: string;
}

export interface NotificationItem {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  data: Record<string, any>;
  read: boolean;
  dismissed: boolean;
  snoozed_until?: string;
  created_at: string;
}

export interface ReminderItem {
  id: number;
  text: string;
  due_at?: string;
  completed: boolean;
  snoozed_until?: string;
  recurring_cron?: string;
  project_id?: string;
  created_at: string;
}

export interface AutomationStatusResponse {
  is_paused: boolean;
  active_count: number;
  paused_count: number;
  disabled_count: number;
  total_count: number;
  running_workflows_count: number;
  unread_notifications_count: number;
  pending_reminders_count: number;
  next_scheduled_run?: string;
}

export interface RoutineTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  autonomy_level: AutonomyLevel;
  action_type: AutomationActionType;
  trigger_config: TriggerConfig;
  action_payload: Record<string, any>;
}

// ==========================================
// NOVA v0.8 Adaptive Intelligence & Personalization Types
// ==========================================

export type PreferenceCategory =
  | "response_length"
  | "explanation_depth"
  | "programming_language"
  | "development_tools"
  | "communication_style"
  | "notification_behavior"
  | "voice_response"
  | "automation_schedule"
  | "general";

export type PreferenceSource = "explicit_ui" | "explicit_voice" | "explicit_chat" | "inferred";

export interface UserPreference {
  id: number;
  key: string;
  category: PreferenceCategory;
  value: any;
  is_explicit: boolean;
  source: PreferenceSource;
  confidence: number;
  context_scope?: string;
  created_at: string;
  updated_at: string;
}

export type RecommendationStatus = "pending" | "accepted" | "dismissed" | "executed";

export interface Recommendation {
  id: string;
  text: string;
  evidence: string[];
  related_project?: string;
  related_task?: string;
  confidence: number;
  reason: string;
  suggested_action?: string;
  status: RecommendationStatus;
  created_at: string;
}

export type EntityType =
  | "project"
  | "technology"
  | "task"
  | "decision"
  | "document"
  | "workflow"
  | "preference"
  | "knowledge_item";

export type RelationType =
  | "USES"
  | "HAS_TASK"
  | "HAS_DECISION"
  | "BELONGS_TO"
  | "REFERENCES"
  | "APPLIES_TO"
  | "DEPENDS_ON"
  | "RELATED_TO";

export interface KnowledgeEntity {
  id: string;
  name: string;
  entity_type: EntityType;
  project_id?: string;
  properties: Record<string, any>;
  confidence: number;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeRelation {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: RelationType;
  project_id?: string;
  confidence: number;
  source: string;
  created_at: string;
}

export interface KnowledgeGraphView {
  entities: KnowledgeEntity[];
  relations: KnowledgeRelation[];
  total_entities: number;
  total_relations: number;
}

export interface ResolvedContext {
  active_project?: string;
  context_source: string;
  confidence: number;
  project_memory_count: number;
  active_window_title?: string;
  active_window_app?: string;
  active_workflow_id?: string;
  active_workflow_state?: string;
  pending_routines_count: number;
  clarification_needed: boolean;
  clarification_prompt?: string;
  active_preferences: Record<string, any>;
  candidate_projects: string[];
}

export type FeedbackType =
  | "useful"
  | "dismiss_permanent"
  | "preference_correction"
  | "association_incorrect"
  | "forget_preference";

export interface FeedbackRecord {
  id: number;
  feedback_type: FeedbackType;
  target_id?: string;
  user_correction?: string;
  updated_state: Record<string, any>;
  created_at: string;
}

export interface PersonalizationPrivacySettings {
  enabled: boolean;
  adaptive_analysis_enabled: boolean;
  recommendations_enabled: boolean;
  store_inferred_preferences: boolean;
  active_window_awareness_enabled: boolean;
  voice_personalization_enabled: boolean;
}

export interface PersonalizationStatus {
  enabled: boolean;
  adaptive_analysis_enabled: boolean;
  recommendations_enabled: boolean;
  total_preferences: number;
  explicit_preferences_count: number;
  inferred_preferences_count: number;
  total_graph_entities: number;
  total_graph_relations: number;
  pending_recommendations_count: number;
  active_project?: string;
  db_path: string;
}

// ==========================================
// NOVA v0.9 Reliability, Security & Performance Types
// ==========================================

export type SubsystemState = "HEALTHY" | "DEGRADED" | "UNAVAILABLE" | "RECOVERING" | "ERROR";

export interface SubsystemHealth {
  name: string;
  state: SubsystemState;
  message: string;
  latency_ms?: number;
  details: Record<string, any>;
  last_checked: string;
}

export interface SystemHealthSummary {
  overall_status: SubsystemState;
  app_name: string;
  version: string;
  uptime_seconds: number;
  timestamp: string;
  subsystems: Record<string, SubsystemHealth>;
}

export interface DatabaseStatus {
  path: string;
  exists: boolean;
  size_bytes: number;
  wal_size_bytes: number;
  total_size_bytes: number;
  healthy: boolean;
  integrity_status: string;
  journal_mode: string;
  tables_count: number;
  total_records: number;
  table_counts: Record<string, number>;
}

export interface BackupMetadata {
  backup_id: string;
  filename: string;
  path: string;
  trigger: string;
  description: string;
  created_at: string;
  size_bytes: number;
  sha256: string;
  app_version: string;
  tables_count: number;
  total_records: number;
  table_counts: Record<string, number>;
  healthy: boolean;
  file_exists?: boolean;
}

export interface RestorePreview {
  can_restore: boolean;
  backup_id: string;
  confirmation_token?: string;
  target_database?: string;
  current_state?: Record<string, any>;
  backup_state?: Record<string, any>;
  warning?: string;
  error?: string;
}

export interface RecentErrorItem {
  id?: string;
  timestamp: string;
  subsystem: string;
  level?: string;
  severity?: string;
  message: string;
  details?: Record<string, any>;
  exception_type?: string;
  traceback_summary?: string;
}

export interface ConcurrencyMetrics {
  active_inferences: number;
  queued_inferences: number;
  max_concurrent_inferences: number;
  active_ocr: number;
  max_concurrent_ocr: number;
}

export interface OnboardingStatusResponse {
  is_first_run: boolean;
  hardware: {
    cpu_count: number;
    physical_cores: number;
    ram_total_gb: number;
    ram_available_gb: number;
    is_ram_adequate: boolean;
    target_specs: string;
  };
  ollama: {
    online: boolean;
    endpoint: string;
    active_model: string;
    models: string[];
    has_models: boolean;
  };
  voice: {
    input_devices_count: number;
    output_devices_count: number;
    wake_word_phrase: string;
    wake_word_custom_installed: boolean;
    vosk_model_installed: boolean;
    piper_model_installed: boolean;
  };
  database: {
    path: string;
    status: string;
  };
}

export interface OnboardingCompletePayload {
  selected_model?: string;
  voice_enabled?: boolean;
  input_device?: number;
  output_device?: number;
  privacy_screen_enabled?: boolean;
  personalization_enabled?: boolean;
}

export interface UnifiedSettings {
  version: string;
  ai: {
    active_model: string;
    ollama_endpoint: string;
    available_models: string[];
    temperature?: number;
    max_tokens?: number;
    inference?: {
      num_ctx: number;
      num_predict: number;
      num_predict_voice: number;
      num_thread: number | null;
      thread_mode: string;
      keep_alive: string;
      temperature: number;
      max_history_turns: number;
      max_history_turns_voice: number;
      max_concurrent_inference: number;
    };
  };
  voice: {
    wake_word_enabled: boolean;
    voice_mode?: string;
    wake_word_phrase: string;
    wake_word_custom_installed: boolean;
    wake_word_threshold: number;
    input_device?: number;
    output_device?: number;
    speech_rate: number;
    volume: number;
  };
  privacy_and_memory: {
    retention_days: number;
    privacy_mode: boolean;
    screen_capture_allowed: boolean;
    personalization_enabled: boolean;
  };
  database: {
    path: string;
    busy_timeout_ms: number;
    wal_mode: boolean;
  };
}
