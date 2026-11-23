"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  ChevronDown,
  ChevronUp,
  DollarSign,
  ShieldAlert,
} from "lucide-react";
import { Evidence, IncidentEvent, IncidentStatus } from "../types/api";
import { formatCost, formatLatency } from "../lib/utils";

interface AgentTimelineProps {
  events: IncidentEvent[];
  status: IncidentStatus;
  costUsd: number;
  steps: number;
  latencyMs: number;
  onSelectEvidence: (ev: Evidence) => void;
}

interface StepDefinition {
  node: string;
  name: string;
  description: string;
}

const PIPELINE_STEPS: StepDefinition[] = [
  { node: "input_guard", name: "Input Guardrail", description: "PII redaction and prompt-injection scan" },
  { node: "supervisor", name: "Supervisor Planner", description: "Investigation strategy & agent dispatch" },
  { node: "metrics_agent", name: "Metrics Specialist", description: "Z-score anomaly & saturation analysis" },
  { node: "logs_agent", name: "Logs Specialist", description: "Untrusted log clustering & 500 error traces" },
  { node: "runbook_agent", name: "Runbook Specialist", description: "RAG retrieval of service runbooks" },
  { node: "root_cause_agent", name: "Root-Cause Synthesis", description: "Hypothesis generation with confidence" },
  { node: "output_guard", name: "Output Guardrail", description: "Groundedness gate & hallucination check" },
  { node: "human_approval", name: "Human Approval Gate", description: "Remediation permission & capability token" },
];

export function AgentTimeline({
  events,
  status,
  costUsd,
  steps,
  latencyMs,
  onSelectEvidence,
}: AgentTimelineProps) {
  const isRunning = status === "running" || status === "queued";
  const [isExpanded, setIsExpanded] = useState<boolean>(isRunning);

  // Auto expand when running, collapse when finished
  React.useEffect(() => {
    if (isRunning) {
      setIsExpanded(true);
    }
  }, [isRunning]);

  // Determine completed and active nodes from events
  const completedNodes = new Set(
    events.map((e) => e.node)
  );

  const getStepState = (node: string, index: number) => {
    if (completedNodes.has(node)) return "done";

    // Find the first non-completed step
    const firstIncompleteIdx = PIPELINE_STEPS.findIndex(
      (s) => !completedNodes.has(s.node)
    );
    if (isRunning && index === firstIncompleteIdx) return "active";

    return "pending";
  };

  // Find events for each node
  const getEventForNode = (node: string) => {
    return events.filter((e) => e.node === node);
  };

  const completedCount = PIPELINE_STEPS.filter((s) => completedNodes.has(s.node)).length;

  return (
    <div className="bg-zinc-900 border border-zinc-800/80 rounded-xl overflow-hidden shadow-sm transition-all duration-200">
      {/* Timeline Summary Bar / Header */}
      <div
        onClick={() => !isRunning && setIsExpanded(!isExpanded)}
        className={`px-5 py-3.5 flex items-center justify-between transition-colors ${
          !isRunning ? "cursor-pointer hover:bg-zinc-800/40" : ""
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {isRunning ? (
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
              </span>
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            )}
            <span className="text-xs font-semibold text-zinc-100 tracking-tight">
              {isRunning
                ? "Agent Investigation In Progress"
                : `${completedCount} investigation steps completed`}
            </span>
          </div>

          <span className="text-zinc-600 text-xs">|</span>

          {/* Metrics */}
          <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono tabular-nums">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-zinc-500" />
              <span>{latencyMs > 0 ? formatLatency(latencyMs) : "live"}</span>
            </span>
            <span className="flex items-center gap-1">
              <DollarSign className="w-3.5 h-3.5 text-zinc-500" />
              <span>{formatCost(costUsd)}</span>
            </span>
          </div>
        </div>

        {/* Expand/Collapse Toggle Button for Done states */}
        {!isRunning && (
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200">
            <span>{isExpanded ? "Collapse" : "Expand Stepper"}</span>
            {isExpanded ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </div>
        )}
      </div>

      {/* Expanded Stepper Steps */}
      {isExpanded && (
        <div className="px-5 pb-5 pt-2 border-t border-zinc-800/60 divide-y divide-zinc-800/40">
          {PIPELINE_STEPS.map((step, idx) => {
            const stepState = getStepState(step.node, idx);
            const stepEvents = getEventForNode(step.node);
            const latestEvent = stepEvents[stepEvents.length - 1];

            return (
              <div
                key={step.node}
                className="py-3 flex items-start justify-between gap-4 transition-colors"
              >
                {/* Status icon + Title */}
                <div className="flex items-start gap-3 min-w-[200px]">
                  <div className="mt-0.5 shrink-0">
                    {stepState === "done" && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    )}
                    {stepState === "active" && (
                      <span className="flex h-4 w-4 relative items-center justify-center">
                        <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-amber-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400"></span>
                      </span>
                    )}
                    {stepState === "pending" && (
                      <Circle className="w-4 h-4 text-zinc-700" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-medium ${
                          stepState === "done"
                            ? "text-zinc-200"
                            : stepState === "active"
                            ? "text-amber-300 font-semibold"
                            : "text-zinc-500"
                        }`}
                      >
                        {step.name}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      {latestEvent?.summary || step.description}
                    </p>
                  </div>
                </div>

                {/* Evidence Chips emitted by this step */}
                <div className="flex flex-wrap items-center gap-1.5 justify-end">
                  {stepEvents.map((ev) => {
                    if (ev.data && ev.data.evidence && Array.isArray(ev.data.evidence)) {
                      return (ev.data.evidence as Evidence[]).map((e) => (
                        <button
                          key={e.id}
                          onClick={() => onSelectEvidence(e)}
                          className="px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 transition-colors cursor-pointer"
                          title="Click to view raw evidence"
                        >
                          [{e.id}]
                        </button>
                      ));
                    }
                    if (ev.data && ev.data.guardrail_flags && Array.isArray(ev.data.guardrail_flags)) {
                      const flags = ev.data.guardrail_flags;
                      if (flags.length > 0) {
                        return (
                          <span
                            key={ev.id}
                            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/20"
                          >
                            <ShieldAlert className="w-3 h-3" />
                            {flags.length} flag(s)
                          </span>
                        );
                      }
                    }
                    return null;
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
