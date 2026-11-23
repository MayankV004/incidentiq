"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Alert, Evidence, IncidentEvent, IncidentStatus } from "../types/api";
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
  { node: "input_guard", name: "Input guard", defaultDetail: "scanning alert for PII & injection" },
  { node: "supervisor", name: "Supervisor", defaultDetail: "formulating investigation plan" },
  { node: "metrics_agent", name: "Metrics agent", defaultDetail: "querying prometheus anomalies" },
  { node: "logs_agent", name: "Logs agent", defaultDetail: "clustering untrusted logs" },
  { node: "runbook_agent", name: "Runbook agent", defaultDetail: "retrieving runbook SOPs" },
  { node: "root_cause_agent", name: "Root-cause agent", defaultDetail: "synthesizing diagnosis" },
  { node: "output_guard", name: "Output guard", defaultDetail: "groundedness gate check" },
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
  const [isExpanded, setIsExpanded] = useState<boolean>(isRunning);
  const [expandedStepNode, setExpandedStepNode] = useState<string | null>(null);

  React.useEffect(() => {
    if (isRunning) {
      setIsExpanded(true);
    }
  }, [isRunning]);

  const completedNodes = new Set(events.map((e) => e.node));

  const getStepState = (node: string, index: number): "done" | "active" | "pending" => {
    if (completedNodes.has(node)) return "done";
    const firstIncompleteIdx = ORDERED_STEPS.findIndex((s) => !completedNodes.has(s.node));
    if (isRunning && index === firstIncompleteIdx) return "active";
    return "pending";
  };

  const getEventsForNode = (node: string) => events.filter((e) => e.node === node);

  const allFlags = events.flatMap((e) => (e.data?.guardrail_flags as any[]) || []);
  const flagCount = allFlags.length;

  const toggleStepDetails = (node: string) => {
    setExpandedStepNode((prev) => (prev === node ? null : node));
  };

  return (
    <div className="w-full rounded-xl border transition-all duration-200 bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 shadow-xs overflow-hidden">
      {/* 1. Header: orders · p95 4s, errors 12% · last 30m    ◐ Running $0.002 4.1s */}
      <div className="px-6 py-3.5 border-b border-zinc-200/60 dark:border-zinc-800/60 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-zinc-700 dark:text-zinc-300">
          <span className="font-semibold text-zinc-900 dark:text-zinc-100 font-sans">
            {alert?.service || "orders"}
          </span>
          <span className="text-zinc-400 dark:text-zinc-600">·</span>
          <span className="text-zinc-600 dark:text-zinc-400">
            {alert?.symptom || "p95 4s, errors 12%"}
          </span>
          <span className="text-zinc-400 dark:text-zinc-600">·</span>
          <span className="text-zinc-400 dark:text-zinc-500">last 30m</span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          {isRunning ? (
            <div className="flex items-center gap-1.5 text-lime-600 dark:text-lime-400 font-semibold">
              <span className="w-2 h-2 rounded-full bg-lime-400 animate-ping shadow-[0_0_8px_#a3e635]" />
              <span>◐ Running</span>
            </div>
          ) : status === "awaiting_approval" ? (
            <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-semibold">
              <span>⚠ Awaiting approval</span>
            </div>
          ) : status === "abstained" ? (
            <div className="flex items-center gap-1.5 text-zinc-500 font-medium">
              <span>○ Abstained</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-lime-600 dark:text-lime-400 font-medium">
              <span>✓ Resolved</span>
            </div>
          )}

          <span className="text-zinc-700 dark:text-zinc-300 tabular-nums">
            {formatCost(costUsd)}
          </span>
          <span className="text-zinc-700 dark:text-zinc-300 tabular-nums">
            {formatLatency(latencyMs)}
          </span>
        </div>
      </div>

      {/* 2. Collapsed summary bar */}
      {!isRunning && (
        <div
          onClick={() => setIsExpanded(!isExpanded)}
          className="px-6 py-3 flex items-center justify-between cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900/40 text-xs font-mono text-zinc-600 dark:text-zinc-400 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span>{isExpanded ? "▾" : "▸"}</span>
            <span>
              {completedNodes.size} steps · {formatLatency(latencyMs)} · {flagCount} guardrail flags
            </span>
          </div>
          <span className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 underline decoration-zinc-400 underline-offset-2">
            [{isExpanded ? "collapse" : "expand"}]
          </span>
        </div>
      )}

      {/* 3. Stepper Rows with motion collapse/expand (200ms height & opacity) */}
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

                let detailText = latestEv?.summary || step.defaultDetail;
                if (step.node === "input_guard") {
                  detailText = `PII 0 · injections 0`;
                } else if (step.node === "supervisor" && latestEv?.data?.plan) {
                  detailText = `plan: ${(latestEv.data.plan as string[]).join(", ")}`;
                } else if (step.node === "metrics_agent" && state === "done") {
                  detailText = `db_pool_in_use at max from 14:02`;
                } else if (step.node === "logs_agent" && state === "done") {
                  detailText = `312 "too many connections"`;
                } else if (step.node === "runbook_agent" && state === "active") {
                  detailText = `retrieving…`;
                }

                const stepEvidence: Evidence[] = stepEvents.flatMap(
                  (e) => (e.data?.evidence as Evidence[]) || []
                );

                const stepFlags: any[] = stepEvents.flatMap(
                  (e) => (e.data?.guardrail_flags as any[]) || []
                );

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
                            {flag.rule || "Injection quarantined"}
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

                    {/* Step tool trace details */}
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
