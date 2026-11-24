export type IncidentStatus =
  | "idle"
  | "queued"
  | "running"
  | "awaiting_approval"
  | "completed"
  | "abstained"
  | "budget_exceeded"
  | "failed"
  | "remediation_executed"
  | "rejected_by_human";

export interface Alert {
  service: string;
  symptom: string;
  window_start: string;
  window_end: string;
}

export interface Evidence {
  id: string;
  kind?: string;
  source?: "metric" | "log" | "runbook" | "postmortem";
  summary: string;
  source_ref?: string;
  raw_ref?: string;
  confidence?: number;
  data?: Record<string, unknown>;
}

export interface Action {
  type: string;
  target: string;
  detail?: string;
  dry_run_only?: boolean;
  parameters?: Record<string, unknown>;
}

export interface Hypothesis {
  category: string;
  root_cause?: string;
  service?: string;
  confidence: number;
  groundedness_score?: number;
  reasoning: string;
  abstained: boolean;
  abstain_reason?: string;
  evidence_ids?: string[];
  supporting_evidence_ids?: string[];
  suggested_action?: Action | null;
  recommended_action?: Action | null;
}

export interface ApprovalInfo {
  required: boolean;
  approval_id?: string;
  action?: {
    type: string;
    target: string;
    dry_run_only?: boolean;
    parameters?: Record<string, unknown>;
  };
  reason?: string;
}

export interface EvalRunMetrics {
  accuracy?: number;
  accuracy_pct?: number;
  groundedness_pass_rate?: number;
  groundedness_pct?: number;
  abstention_precision?: number;
  abstention_correct_pct?: number;
  avg_latency_ms?: number;
  latency_p50_ms?: number;
  avg_cost_usd?: number;
  mean_cost_usd?: number;
  total_runs?: number;
  simulated?: boolean;
  note?: string;
}

export interface GuardrailFlag {
  rule: string;
  field?: string;
  detail: string;
  action_taken: "redacted" | "sanitized" | "quarantined" | "flagged";
}

export interface IncidentEvent {
  id: string;
  incident_id?: string;
  type:
    | "incident_started"
    | "guardrail_executed"
    | "supervisor_planned"
    | "specialist_completed"
    | "evidence_found"
    | "hypothesis_synthesized"
    | "approval_required"
    | "agent_started"
    | "agent_finished"
    | "done";
  node: string;
  title: string;
  summary: string;
  data?: Record<string, unknown>;
  cost_usd?: number;
  steps?: number;
  timestamp: number;
  status?: IncidentStatus;
}

export interface IncidentDetail {
  incident_id: string;
  scenario_id?: string;
  alert: Alert;
  status: IncidentStatus;
  created_at: number;
  hypothesis?: Hypothesis;
  evidence?: Evidence[];
  guardrail_flags?: GuardrailFlag[];
  approval?: ApprovalInfo;
  cost_usd?: number;
  latency_ms?: number;
  steps?: number;
  remediation_result?: Record<string, unknown>;
  events?: IncidentEvent[];
  langfuse_trace_url?: string;
  error?: string;
}

export interface IncidentSummary {
  incident_id: string;
  service: string;
  symptom: string;
  status: IncidentStatus;
  cost_usd: number;
  latency_ms: number;
  created_at: number;
  category?: string;
  root_cause?: string;
  confidence?: number;
  langfuse_trace_url?: string;
}

export interface Scenario {
  id: string;
  number: string;
  title: string;
  service: string;
  symptom: string;
  expected_root_cause: string;
  expected_action: string;
  window_start: string;
  window_end: string;
}

export interface RedTeamCase {
  id: string;
  category: string;
  payload: string;
  target: string;
  expected_outcome: string;
}
