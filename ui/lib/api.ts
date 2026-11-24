import {
  EvalRunMetrics,
  IncidentDetail,
  IncidentSummary,
  RedTeamCase,
  Scenario,
} from "../types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function extractErrorMessage(res: Response, fallback: string): Promise<string> {
  const errData = (await res.json().catch(() => ({}))) as {
    detail?: string;
    error?: { code?: string; message?: string };
  };
  if (errData?.error?.message) {
    return errData.error.code
      ? `${errData.error.code}: ${errData.error.message}`
      : errData.error.message;
  }
  if (typeof errData?.detail === "string") return errData.detail;
  return `${fallback} (HTTP ${res.status})`;
}

export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "Failed to fetch scenarios"));
  }
  return await res.json();
}

export async function fetchIncidents(): Promise<IncidentSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/incidents`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "Failed to fetch incidents"));
  }
  return await res.json();
}

export async function fetchIncident(id: string): Promise<IncidentDetail> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, `Incident ${id} not found`));
  }
  return await res.json();
}

export async function createIncident(payload: {
  service: string;
  symptom: string;
  window_start?: string;
  window_end?: string;
  scenario_id?: string;
}): Promise<{ incident_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/incidents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "Failed to create incident"));
  }
  return await res.json();
}

export async function submitApproval(
  incidentId: string,
  decision: "approve" | "reject",
  approvalId: string
): Promise<{ status: string; result?: Record<string, unknown>; message?: string }> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${encodeURIComponent(incidentId)}/approval`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, approval_id: approvalId }),
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "Approval request failed"));
  }
  return await res.json();
}

export async function fetchEvalResults(): Promise<Record<string, EvalRunMetrics>> {
  const res = await fetch(`${API_BASE}/api/v1/evals`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "Failed to fetch eval results"));
  }
  return await res.json();
}

export async function fetchRedTeamCases(): Promise<{
  cases: RedTeamCase[];
  total: number;
  blocked_rate?: number;
}> {
  const res = await fetch(`${API_BASE}/api/v1/redteam`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res, "Failed to fetch red-team cases"));
  }
  return await res.json();
}
