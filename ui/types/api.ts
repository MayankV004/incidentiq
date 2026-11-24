export type IncidentStatus =
  | "idle"
  | "queued"
  | "running"
  | "awaiting_approval"
  | "completed"
  | "abstained"
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
  source: "metric" | "log" | "runbook" | "postmortem";
  summary: string;
  raw_ref?: string;
  confidence?: number;
  data?: Record<string, unknown>;
}

export interface Hypothesis {
  root_cause: string;
  confidence: number;
  groundedness_score: number;
  abstained: boolean;
  abstain_reason?: string;
  supporting_evidence_ids: string[];
  recommended_action: {
    type: string;
    target: string;
    dry_run_only?: boolean;
    parameters?: Record<string, unknown>;
  };
}

export interface ApprovalInfo {
  required: boolean;
  approval_id?: string;
  approval_token?: string;
  action?: {
    type: string;
    target: string;
    dry_run_only?: boolean;
    parameters?: Record<string, unknown>;
  };
  reason?: string;
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
