"use client";

import React, { useState } from "react";
import { CheckCircle2, ShieldCheck } from "lucide-react";
import { Evidence, Hypothesis, IncidentDetail, IncidentStatus } from "../types/api";

interface ReportViewProps {
  incident: IncidentDetail | null;
  status: IncidentStatus;
  hypothesis: Hypothesis | null;
  evidenceList: Evidence[];
  onSelectEvidence: (ev: Evidence) => void;
  onRequestApproval: () => void;
  onReject: () => void;
  remediationResult?: Record<string, unknown>;
}

export function ReportView({
  incident,
  status,
  hypothesis,
  evidenceList,
  onSelectEvidence,
  onRequestApproval,
  onReject,
}: ReportViewProps) {
  const [activeTab, setActiveTab] = useState<"report" | "evidence" | "trace">("report");

  if (!hypothesis && (!evidenceList || evidenceList.length === 0)) {
    return null;
  }

  const confidencePct = hypothesis ? Math.round(hypothesis.confidence * 100) : 0;
  const groundednessPct =
    hypothesis?.groundedness_score !== undefined
      ? Math.round(hypothesis.groundedness_score * 100)
      : null;
  const isAwaitingApproval = status === "awaiting_approval";
  const isExecuted = status === "remediation_executed";
  const isRejected = status === "rejected_by_human";

  return (
    <div className="w-full rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 overflow-hidden shadow-xs transition-colors">
      {/* 1. Wireframe Tabs: Report   Evidence (3)   Trace */}
      <div className="px-6 pt-3.5 border-b border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <button
            onClick={() => setActiveTab("report")}
            className={`pb-3 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === "report"
                ? "border-lime-500 text-zinc-900 dark:text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            Report
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`pb-3 text-xs font-medium border-b-2 flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeTab === "evidence"
                ? "border-lime-500 text-zinc-900 dark:text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            <span>Evidence ({evidenceList.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("trace")}
            className={`pb-3 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === "trace"
                ? "border-lime-500 text-zinc-900 dark:text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            Trace
          </button>
        </div>

        {/* Confidence & Groundedness Meters */}
        <div className="flex items-center gap-5 pb-3 font-mono text-xs">
          <div className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-400">
            <span>Confidence</span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">{confidencePct}%</span>
          </div>
          <div className="flex items-center gap-1.5 text-lime-600 dark:text-lime-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Groundedness {groundednessPct !== null ? `${groundednessPct}%` : "—"}</span>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "report" && (
        <div className="p-6 space-y-6 text-sm">
          {/* Header Title: Dynamic Category & Service */}
          <div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight capitalize">
              {hypothesis?.abstained
                ? `Abstained: Inconclusive Telemetry${hypothesis?.service ? ` · ${hypothesis.service}` : ""}`
                : `${(hypothesis?.category || hypothesis?.root_cause || "Uncertain Root Cause").replace(/_/g, " ")}${
                    hypothesis?.service ? ` · ${hypothesis.service}` : ""
                  }`}
            </h2>
          </div>

          {/* Narrative Body with dynamic reasoning and clickable evidence chips */}
          <div className="text-zinc-700 dark:text-zinc-300 leading-relaxed space-y-3 font-sans">
            <p>
              {hypothesis?.abstained
                ? hypothesis?.abstain_reason || "Telemetry is inconclusive or inconsistent with known failure models."
                : hypothesis?.reasoning || "Investigation concluded with insufficient telemetry details."}
            </p>

            {evidenceList && evidenceList.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-2">
                <span className="text-xs text-zinc-500 font-mono">Cited evidence:</span>
                {evidenceList.map((e) => (
                  <button
                    key={e.id}
                    onClick={() => onSelectEvidence(e)}
                    className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 cursor-pointer hover:border-lime-500 transition-colors"
                  >
                    {e.id}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Suggested action line: dynamic action details */}
          {hypothesis?.suggested_action && (
            <div className="pt-4 border-t border-zinc-200/60 dark:border-zinc-800/60 space-y-4">
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="text-zinc-400">Suggested action</span>
                <span className="text-zinc-900 dark:text-zinc-100 font-semibold">
                  {hypothesis.suggested_action.type} → {hypothesis.suggested_action.target}
                  {hypothesis.suggested_action.detail ? ` · ${hypothesis.suggested_action.detail}` : ""}
                </span>
              </div>

              {/* Awaiting Approval Actions: [ Approve (dry-run) ]  [ Reject ] */}
              {isAwaitingApproval && (
                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={onRequestApproval}
                    className="px-5 py-2.5 rounded-lg text-xs font-semibold bg-lime-400 hover:bg-lime-300 dark:bg-lime-400 dark:hover:bg-lime-300 text-zinc-950 shadow-[0_0_16px_rgba(163,230,53,0.35)] transition-all active:scale-98 cursor-pointer"
                  >
                    Approve (dry-run)
                  </button>
                  <button
                    onClick={onReject}
                    className="px-4 py-2 rounded-lg text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
                  >
                    Reject
                  </button>
                </div>
              )}

              {/* Executed Receipt in Mono: "Executed as dry-run. No changes made." */}
              {isExecuted && (
                <div className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 font-mono text-xs space-y-2">
                  <div className="flex items-center gap-2 text-lime-600 dark:text-lime-400 font-semibold">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Executed as dry-run. No changes made.</span>
                  </div>
                  <div className="text-[11px] text-zinc-500 space-y-0.5">
                    <div>Action: {hypothesis.suggested_action.type} ({hypothesis.suggested_action.target})</div>
                    <div>Capability Token: Verified single-use token</div>
                    {hypothesis.suggested_action.detail && <div>Detail: {hypothesis.suggested_action.detail}</div>}
                  </div>
                </div>
              )}

              {isRejected && (
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-mono text-zinc-500">
                  Action rejected by engineer. Incident marked resolved.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Evidence */}
      {activeTab === "evidence" && (
        <div className="p-6 divide-y divide-zinc-100 dark:divide-zinc-800/60 font-mono text-xs">
          {evidenceList.map((ev) => (
            <div key={ev.id} className="py-3.5 flex items-start justify-between gap-4 first:pt-0 last:pb-0">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100">{ev.id}</span>
                  <span className="text-[10px] uppercase px-1.5 py-0.2 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                    {ev.source}
                  </span>
                </div>
                <p className="font-sans text-xs text-zinc-600 dark:text-zinc-300">{ev.summary}</p>
              </div>

              <button
                onClick={() => onSelectEvidence(ev)}
                className="px-2.5 py-1 rounded text-xs bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 transition-colors cursor-pointer hover:border-lime-500"
              >
                Inspect
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Trace */}
      {activeTab === "trace" && (
        <div className="p-6 space-y-4 font-mono text-xs">
          {incident?.langfuse_trace_url && (
            <div className="p-3.5 rounded-lg bg-lime-400/10 border border-lime-400/30 flex items-center justify-between text-xs font-sans">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-lime-400 animate-pulse" />
                <span className="text-zinc-800 dark:text-zinc-200 font-medium">
                  Full LLM Waterfall Trace Available in Langfuse
                </span>
              </div>
              <a
                href={incident.langfuse_trace_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-lg bg-lime-400 hover:bg-lime-300 text-zinc-950 font-semibold text-xs transition-all flex items-center gap-1.5 shadow-[0_0_10px_rgba(163,230,53,0.35)] cursor-pointer"
              >
                <span>Open in Langfuse</span>
                <span>↗</span>
              </a>
            </div>
          )}

          <div className="space-y-2">
            {(incident?.events || []).map((ev, i) => (
              <div
                key={ev.id || i}
                className="flex items-center justify-between py-2 border-b border-zinc-100 dark:border-zinc-800/40 text-zinc-700 dark:text-zinc-300"
              >
                <div className="flex items-center gap-2">
                  <span className="text-zinc-400">{i + 1}.</span>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100">{ev.node}</span>
                </div>
                <span className="text-zinc-500 truncate max-w-sm">{ev.summary}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
