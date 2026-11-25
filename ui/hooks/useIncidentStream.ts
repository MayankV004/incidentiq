"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApprovalInfo,
  Evidence,
  GuardrailFlag,
  Hypothesis,
  IncidentDetail,
  IncidentEvent,
  IncidentStatus,
} from "../types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const TERMINAL_STATUSES = new Set<IncidentStatus>([
  "completed",
  "awaiting_approval",
  "abstained",
  "budget_exceeded",
  "failed",
  "remediation_executed",
  "rejected_by_human",
]);

export function useIncidentStream(
  incidentId: string | null,
  onNotFound?: () => void
) {
  const [loadedIncidentId, setLoadedIncidentId] = useState<string | null>(null);
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [status, setStatus] = useState<IncidentStatus>("idle");
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [hypothesis, setHypothesis] = useState<Hypothesis | null>(null);
  const [approval, setApproval] = useState<ApprovalInfo | null>(null);
  const [guardrailFlags, setGuardrailFlags] = useState<GuardrailFlag[]>([]);
  const [costUsd, setCostUsd] = useState<number>(0);
  const [steps, setSteps] = useState<number>(0);
  const [latencyMs, setLatencyMs] = useState<number>(0);
  const [langfuseTraceUrl, setLangfuseTraceUrl] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const onNotFoundRef = useRef(onNotFound);
  useEffect(() => {
    onNotFoundRef.current = onNotFound;
  }, [onNotFound]);

  const applyIncidentDetail = useCallback((id: string, data: IncidentDetail) => {
    setLoadedIncidentId(id);
    setIncident(data);
    setStatus(data.status || "idle");
    setHypothesis(data.hypothesis ?? null);
    setEvidenceList(Array.isArray(data.evidence) ? data.evidence : []);
    setApproval(data.approval ?? null);
    setGuardrailFlags(Array.isArray(data.guardrail_flags) ? data.guardrail_flags : []);
    setCostUsd(data.cost_usd ?? 0);
    setLatencyMs(data.latency_ms ?? 0);
    setSteps(data.steps ?? 0);
    setEvents(Array.isArray(data.events) ? data.events : []);
    setLangfuseTraceUrl(data.langfuse_trace_url ?? null);
    if (data.error) setError(data.error);
    else if (data.status === "budget_exceeded") {
      setError("Incident terminated because the agent step or cost budget was exceeded.");
    } else {
      setError(null);
    }
  }, []);

  const refreshIncident = useCallback(async () => {
    if (!incidentId) return;
    try {
      const r = await fetch(`${API_BASE}/api/v1/incidents/${encodeURIComponent(incidentId)}`, {
        cache: "no-store",
      });
      if (!r.ok) return;
      const data = (await r.json()) as IncidentDetail;
      applyIncidentDetail(incidentId, data);
    } catch {
      // ignore transient refresh failure
    }
  }, [incidentId, applyIncidentDetail]);

  useEffect(() => {
    if (!incidentId) {
      return;
    }

    let isMounted = true;
    let eventSource: EventSource | null = null;
    const controller = new AbortController();

    const fetchDetail = async (): Promise<IncidentDetail | null> => {
      const r = await fetch(`${API_BASE}/api/v1/incidents/${encodeURIComponent(incidentId)}`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (r.status === 404) {
        if (isMounted) onNotFoundRef.current?.();
        return null;
      }
      if (!r.ok) {
        throw new Error(`HTTP ${r.status}`);
      }
      return (await r.json()) as IncidentDetail;
    };

    const startStream = () => {
      eventSource = new EventSource(
        `${API_BASE}/api/v1/incidents/${encodeURIComponent(incidentId)}/stream`
      );

      eventSource.onopen = () => {
        if (!isMounted) return;
        setLoadedIncidentId(incidentId);
        setError(null);
        setIsStreaming(true);
        setStatus((prev) => (TERMINAL_STATUSES.has(prev) ? prev : "running"));
      };

      eventSource.onmessage = (e) => {
        if (!isMounted) return;
        try {
          const ev: IncidentEvent = JSON.parse(e.data);
          setLoadedIncidentId(incidentId);
          setEvents((prev) => {
            if (prev.some((p) => p.id === ev.id)) return prev;
            return [...prev, ev];
          });

          if (ev.cost_usd !== undefined) setCostUsd(ev.cost_usd);
          if (ev.steps !== undefined) setSteps(ev.steps);

          if (ev.data) {
            const d = ev.data as Record<string, unknown>;
            if (d.evidence && Array.isArray(d.evidence)) {
              setEvidenceList((prev) => {
                const ids = new Set(prev.map((item) => item.id));
                const newItems = (d.evidence as Evidence[]).filter((item) => !ids.has(item.id));
                return [...prev, ...newItems];
              });
            }
            if (d.hypothesis) {
              setHypothesis(d.hypothesis as Hypothesis);
            }
            if (d.approval) {
              setApproval(d.approval as ApprovalInfo);
            }
            if (d.guardrail_flags && Array.isArray(d.guardrail_flags)) {
              setGuardrailFlags((prev) => [
                ...prev,
                ...(d.guardrail_flags as GuardrailFlag[]),
              ]);
            }
            if (d.latency_ms && typeof d.latency_ms === "number") {
              setLatencyMs(d.latency_ms);
            }
            if (d.langfuse_trace_url && typeof d.langfuse_trace_url === "string") {
              setLangfuseTraceUrl(d.langfuse_trace_url);
            }
          }

          if (ev.type === "done" && ev.status) {
            setStatus(ev.status);
            if (ev.status === "budget_exceeded") {
              setError("Incident terminated because the agent step or cost budget was exceeded.");
            } else if (ev.status === "failed" && ev.summary) {
              setError(ev.summary);
            }
            setIsStreaming(false);
            eventSource?.close();
            fetchDetail()
              .then((full) => {
                if (isMounted && full) applyIncidentDetail(incidentId, full);
              })
              .catch(() => {});
          }
        } catch (err) {
          console.error("Failed to parse SSE event:", err);
        }
      };

      eventSource.onerror = () => {
        if (!isMounted) return;
        eventSource?.close();
        setIsStreaming(false);
        fetchDetail()
          .then((data) => {
            if (isMounted && data) applyIncidentDetail(incidentId, data);
          })
          .catch((err) => {
            if (!isMounted || controller.signal.aborted) return;
            setLoadedIncidentId(incidentId);
            setError(String(err));
          });
      };
    };

    fetchDetail()
      .then((data) => {
        if (!isMounted || !data) return;
        applyIncidentDetail(incidentId, data);
        if (TERMINAL_STATUSES.has(data.status)) {
          setIsStreaming(false);
          return;
        }
        startStream();
      })
      .catch((err) => {
        if (!isMounted || controller.signal.aborted) return;
        setLoadedIncidentId(incidentId);
        setError(String(err));
      });

    return () => {
      isMounted = false;
      controller.abort();
      eventSource?.close();
    };
  }, [incidentId, applyIncidentDetail]);

  const isCurrent = Boolean(incidentId && loadedIncidentId === incidentId);

  return {
    incident: isCurrent ? incident : null,
    events: isCurrent ? events : [],
    status: isCurrent ? status : incidentId ? "running" : "idle",
    setStatus,
    refreshIncident,
    evidenceList: isCurrent ? evidenceList : [],
    hypothesis: isCurrent ? hypothesis : null,
    approval: isCurrent ? approval : null,
    guardrailFlags: isCurrent ? guardrailFlags : [],
    costUsd: isCurrent ? costUsd : 0,
    steps: isCurrent ? steps : 0,
    latencyMs: isCurrent ? latencyMs : 0,
    langfuseTraceUrl: isCurrent ? langfuseTraceUrl : null,
    isStreaming: isCurrent ? isStreaming : Boolean(incidentId),
    error: isCurrent ? error : null,
  };
}
