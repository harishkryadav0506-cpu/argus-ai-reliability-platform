/**
 * ARGUS Frontend TypeScript Type Definitions (Section 22, 23, 24)
 */

export interface MetricSnapshot {
  timestamp: string;
  latency: number;
  error_rate: number;
  token_count: number;
  cost_per_query: number;
  retrieval_score: number;
  answer_relevance: number;
  tool_failure_rate: number;
  loop_count: number;
  api_success_rate: number;
  cpu_utilization: number;
  [key: string]: number | string;
}

export interface MetricsResponse {
  current: MetricSnapshot;
  history: MetricSnapshot[];
  count: number;
}

export interface IncidentMetric {
  id: string;
  incident_id: string;
  metric_name: string;
  value: number;
  timestamp: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'unknown';
  status: 'open' | 'investigating' | 'resolved' | 'escalated' | 'closed';
  failure_type: string;
  confidence: number;
  created_at: string;
  resolved_at?: string | null;
  metrics?: IncidentMetric[];
}

export interface StrategyOption {
  id?: string;
  action?: string;
  strategy?: string;
  parameters?: Record<string, any>;
  success_probability?: number;
  recovery_probability?: number;
  risk_score?: number;
  risk?: 'low' | 'medium' | 'high' | string;
  reversibility?: 'instant' | 'reversible' | 'irreversible' | string;
  side_effects?: string;
  rationale?: string;
  potential_impact?: string | null;
}

export interface RecoveryOptionsResponse {
  incident_id: string;
  failure_type: string;
  approval_required: boolean;
  risk_score: number;
  recommended_strategy: StrategyOption;
  strategies: StrategyOption[];
}

export interface ApprovalResponse {
  incident_id: string;
  approval_status: 'approved' | 'rejected' | 'pending';
  execution_status: string;
  message: string;
  details?: Record<string, any>;
  verification?: {
    recovery_verified?: boolean;
    [key: string]: any;
  };
}

export interface RunbookCitation {
  source: string;
  relevance_score: number;
  document: string;
  chunk: string;
}

export interface DiagnosisResponse {
  incident_id: string;
  failure_type: string;
  confidence: number;
  root_cause: string;
  evidence: string[];
  citations: RunbookCitation[];
}

export interface BenchmarkMetricsComparison {
  detection_f1: number;
  detection_accuracy: number;
  detection_recall: number;
  diagnosis_accuracy: number;
  rag_retrieval_score: number;
  recovery_success_rate: number;
  unsafe_action_rate: number;
  mean_recovery_time_sec: number;
  average_latency: number;
}

export interface BenchmarkResult {
  benchmark_id: string;
  evaluated_at?: string;
  executed_at?: string;
  scenarios_evaluated?: number;
  total_scenarios?: number;
  v1_baseline: BenchmarkMetricsComparison;
  v2_argus: BenchmarkMetricsComparison;
  delta?: Record<string, number>;
  deltas?: Record<string, number>;
  markdown_report?: string;
}

export interface HealthServiceStatus {
  status: string;
  [key: string]: any;
}

export interface HealthResponse {
  status: string;
  environment: string;
  services: {
    database: string | HealthServiceStatus;
    llm: HealthServiceStatus;
    langsmith: HealthServiceStatus;
    redis: HealthServiceStatus;
    vector_db: HealthServiceStatus;
    mcp: HealthServiceStatus;
  };
}
