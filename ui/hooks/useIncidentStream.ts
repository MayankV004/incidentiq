"use client";

import { useEffect, useState } from "react";
import {
  ApprovalInfo,
  Evidence,
  GuardrailFlag,
  Hypothesis,
  IncidentEvent,
  IncidentStatus,
} from "../types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useIncidentStream(incidentId: string | null) {
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [status, setStatus] = useState<IncidentStatus>("idle");
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [hypothesis, setHypothesis] = useState<Hypothesis | null>(null);
  const [approval, setApproval] = useState<ApprovalInfo | null>(null);
  const [guardrailFlags, setGuardrailFlags] = useState<GuardrailFlag[]>([]);
  const [costUsd, setCostUsd] = useState<number>(0);
  const [steps, setSteps] = useState<number>(0);
  const [latencyMs, setLatencyMs] = useState<number>(0);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!incidentId) {
      setEvents([]);
      setStatus("idle");
      setEvidenceList([]);
      setHypothesis(null);
      setApproval(null);
      setGuardrailFlags([]);
      setCostUsd(0);
      setSteps(0);
      setLatencyMs(0);
      setIsStreaming(false);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsStreaming(true);
    setStatus("running");

    const eventSource = new EventSource(`${API_BASE}/v1/incidents/${incidentId}/stream`);

    eventSource.onmessage = (e) => {
      if (!isMounted) return;
      try {
        const ev: IncidentEvent = JSON.parse(e.data);
        setEvents((prev) => {
          if (prev.some((p) => p.id === ev.id)) return prev;
          return [...prev, ev];
        });

        if (ev.cost_usd !== undefined) setCostUsd(ev.cost_usd);
        if (ev.steps !== undefined) setSteps(ev.steps);

        // Process typed data payload
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
        }

        // Check terminal state
        if (ev.type === "done" && ev.status) {
          setStatus(ev.status);
          setIsStreaming(false);
          eventSource.close();
        }
      } catch (err) {
        console.error("Failed to parse SSE event:", err);
      }
    };

    eventSource.onerror = () => {
      if (!isMounted) return;
      // On error, close eventSource and perform single REST poll fallback
      eventSource.close();
      setIsStreaming(false);

      fetch(`${API_BASE}/v1/incidents/${incidentId}`)
        .then((r) => r.json())
        .then((data) => {
          if (!isMounted) return;
          if (data.status) setStatus(data.status);
          if (data.hypothesis) setHypothesis(data.hypothesis);
          if (data.evidence) setEvidenceList(data.evidence);
          if (data.approval) setApproval(data.approval);
          if (data.guardrail_flags) setGuardrailFlags(data.guardrail_flags);
          if (data.cost_usd) setCostUsd(data.cost_usd);
          if (data.latency_ms) setLatencyMs(data.latency_ms);
          if (data.steps) setSteps(data.steps);
          if (data.events) setEvents(data.events);
        })
        .catch((err) => {
          if (!isMounted) return;
          setError(String(err));
        });
    };

    return () => {
      isMounted = false;
      eventSource.close();
    };
  }, [incidentId]);

  return {
    events,
    status,
    setStatus,
    evidenceList,
    hypothesis,
    approval,
    guardrailFlags,
    costUsd,
    steps,
    latencyMs,
    isStreaming,
    error,
  };
}
