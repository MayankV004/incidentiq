"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Alert, Evidence, GuardrailFlag, IncidentEvent, IncidentStatus } from "../types/api";
import { formatCost, formatLatency } from "../lib/utils";

interface AgentTimelineProps {
  alert?: Alert;
  events: IncidentEvent[];
  status: IncidentStatus;
  costUsd: number;
  steps: number;
  latencyMs: number;
  onSelectEvidence: (ev: Evidence) => void;
}

interface StepMeta {
  node: string;
  name: string;
  defaultDetail: string;
}

const ORDERED_STEPS: StepMeta[] = [
  { node: "input_guard", name: "Input guard", defaultDetail: "waiting for input scan" },
  { node: "supervisor", name: "Supervisor", defaultDetail: "pending investigation plan" },
  { node: "metrics_agent", name: "Metrics agent", defaultDetail: "pending metrics query" },
  { node: "logs_agent", name: "Logs agent", defaultDetail: "pending log clustering" },
  { node: "runbook_agent", name: "Runbook agent", defaultDetail: "pending runbook retrieval" },
  { node: "root_cause_agent", name: "Root-cause agent", defaultDetail: "pending synthesis" },
  { node: "output_guard", name: "Output guard", defaultDetail: "pending groundedness check" },
];

export function AgentTimeline({
  alert,
  events,
  status,
  costUsd,
  steps,
  latencyMs,
  onSelectEvidence,
}: AgentTimelineProps) {
  const isRunning = status === "running" || status === "queued";
  const [userExpanded, setUserExpanded] = useState<boolean | null>(null);
  const [expandedStepNode, setExpandedStepNode] = useState<string | null>(null);

  const isExpanded = userExpanded ?? isRunning;
  const completedNodes = new Set(events.map((e) => e.node));

  const getStepState = (node: string, index: number): "done" | "active" | "pending" => {
    if (completedNodes.has(node)) return "done";
    const firstIncompleteIdx = ORDERED_STEPS.findIndex((s) => !completedNodes.has(s.node));
    if (isRunning && index === firstIncompleteIdx) return "active";
    return "pending";
  };

  const getEventsForNode = (node: string) => events.filter((e) => e.node === node);

  const allFlags = events.flatMap(
    (e) => (e.data?.guardrail_flags as GuardrailFlag[] | undefined) || []
  );
  const flagCount = allFlags.length;
  const displayedSteps = steps > 0 ? steps : completedNodes.size;

  const toggleStepDetails = (node: string) => {
    setExpandedStepNode((prev) => (prev === node ? null : node));
  };

  const renderStatusBadge = () => {
    if (isRunning) {
      return (
        <div className="flex items-center gap-1.5 text-lime-600 dark:text-lime-400 font-semibold">
          <span className="w-2 h-2 rounded-full bg-lime-400 animate-ping shadow-[0_0_8px_#a3e635]" />
          <span>◐ Running</span>
        </div>
      );
    }
    if (status === "awaiting_approval") {
      return (
        <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-semibold">
          <span>⚠ Awaiting approval</span>
        </div>
      );
    }
    if (status === "abstained") {
      return (
        <div className="flex items-center gap-1.5 text-zinc-500 font-medium">
          <span>○ Abstained</span>
        </div>
      );
    }
    if (status === "budget_exceeded") {
      return (
        <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-semibold">
          <span>⚠ Budget exceeded</span>
        </div>
      );
    }
    if (status === "failed") {
      return (
        <div className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-semibold">
          <span>✕ Failed</span>
        </div>
      );
    }
    if (status === "rejected_by_human") {
      return (
        <div className="flex items-center gap-1.5 text-zinc-500 font-medium">
          <span>○ Rejected</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 text-lime-600 dark:text-lime-400 font-medium">
        <span>✓ Resolved</span>
      </div>
    );
  };

  return (
    <div className="w-full rounded-xl border transition-all duration-200 bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 shadow-xs overflow-hidden">
      <div className="px-6 py-3.5 border-b border-zinc-200/60 dark:border-zinc-800/60 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-zinc-700 dark:text-zinc-300">
          <span className="font-semibold text-zinc-900 dark:text-zinc-100 font-sans">
            {alert?.service || "—"}
          </span>
          <span className="text-zinc-400 dark:text-zinc-600">·</span>
          <span className="text-zinc-600 dark:text-zinc-400">
            {alert?.symptom || "No symptom reported"}
          </span>
          {alert?.window_start && alert?.window_end && (
            <>
              <span className="text-zinc-400 dark:text-zinc-600">·</span>
              <span className="text-zinc-400 dark:text-zinc-500">
                {alert.window_start} → {alert.window_end}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          {renderStatusBadge()}

          <span className="text-zinc-700 dark:text-zinc-300 tabular-nums">
            {formatCost(costUsd)}
          </span>
          <span className="text-zinc-700 dark:text-zinc-300 tabular-nums">
            {formatLatency(latencyMs)}
          </span>
        </div>
      </div>

      {!isRunning && (
        <div
          onClick={() => setUserExpanded(!isExpanded)}
          className="px-6 py-3 flex items-center justify-between cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900/40 text-xs font-mono text-zinc-600 dark:text-zinc-400 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span>{isExpanded ? "▾" : "▸"}</span>
            <span>
              {displayedSteps} steps · {formatLatency(latencyMs)} · {flagCount} guardrail flags
            </span>
          </div>
          <span className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 underline decoration-zinc-400 underline-offset-2">
            [{isExpanded ? "collapse" : "expand"}]
          </span>
        </div>
      )}

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden border-t border-zinc-100 dark:border-zinc-800/40"
          >
            <div className="px-6 py-3.5 divide-y divide-zinc-100 dark:divide-zinc-800/40">
              {ORDERED_STEPS.map((step, idx) => {
                const state = getStepState(step.node, idx);
                const stepEvents = getEventsForNode(step.node);
                const latestEv = stepEvents[stepEvents.length - 1];

                const stepEvidence: Evidence[] = stepEvents.flatMap(
                  (e) => (e.data?.evidence as Evidence[] | undefined) || []
                );
                const stepFlags: GuardrailFlag[] = stepEvents.flatMap(
                  (e) => (e.data?.guardrail_flags as GuardrailFlag[] | undefined) || []
                );

                let detailText = latestEv?.summary || step.defaultDetail;
                if (step.node === "supervisor" && Array.isArray(latestEv?.data?.plan)) {
                  detailText = `plan: ${(latestEv.data.plan as string[]).join(", ")}`;
                } else if (state === "active" && !latestEv) {
                  detailText = "running…";
                }

                const isStepExpanded = expandedStepNode === step.node;

                return (
                  <div key={step.node} className="py-2.5 space-y-2">
                    <div
                      onClick={() => toggleStepDetails(step.node)}
                      className="flex items-center justify-between gap-4 cursor-pointer group"
                    >
                      <div className="flex items-center gap-3 font-mono text-xs overflow-hidden">
                        <span
                          className={`w-4 text-center shrink-0 ${
                            state === "done"
                              ? "text-lime-600 dark:text-lime-400 font-bold"
                              : state === "active"
                              ? "text-lime-500 dark:text-lime-400 font-bold animate-pulse"
                              : "text-zinc-400 dark:text-zinc-600"
                          }`}
                        >
                          {state === "done" ? "✓" : state === "active" ? "◐" : "○"}
                        </span>

                        <span
                          className={`w-40 shrink-0 font-medium ${
                            state === "done"
                              ? "text-zinc-900 dark:text-zinc-100 font-semibold"
                              : state === "active"
                              ? "text-lime-600 dark:text-lime-400 font-semibold"
                              : "text-zinc-400 dark:text-zinc-500"
                          }`}
                        >
                          {step.name}
                        </span>

                        <span
                          className={`truncate ${
                            state === "done"
                              ? "text-zinc-600 dark:text-zinc-400"
                              : state === "active"
                              ? "text-lime-600/90 dark:text-lime-400/90 italic"
                              : "text-zinc-400 dark:text-zinc-600"
                          }`}
                        >
                          {detailText}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 font-mono text-xs">
                        {stepFlags.map((flag, fIdx) => (
                          <span
                            key={fIdx}
                            className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                          >
                            {flag.rule || "Guardrail triggered"}
                          </span>
                        ))}

                        {stepEvidence.map((ev) => (
                          <motion.button
                            key={ev.id}
                            initial={{ scale: 0.85, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            transition={{ duration: 0.15 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectEvidence(ev);
                            }}
                            className="px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 transition-colors shadow-2xs cursor-pointer hover:border-lime-500"
                            title="Click to inspect raw evidence sheet"
                          >
                            {ev.id}
                          </motion.button>
                        ))}
                      </div>
                    </div>

                    <AnimatePresence>
                      {isStepExpanded && latestEv && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.15 }}
                          className="ml-7 overflow-hidden"
                        >
                          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 font-mono text-[11px] space-y-1.5 my-1">
                            <div className="flex items-center justify-between text-zinc-400">
                              <span>Node Trace: {latestEv.node}</span>
                              <span>Cost: {formatCost(latestEv.cost_usd)}</span>
                            </div>
                            {latestEv.data && (
                              <pre className="text-zinc-700 dark:text-zinc-300 overflow-x-auto max-h-40 leading-snug p-2 rounded bg-white dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-800/60">
                                {JSON.stringify(latestEv.data, null, 2)}
                              </pre>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
