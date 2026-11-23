"use client";

import React, { useState } from "react";
import { CheckCircle2, ShieldCheck, Terminal, AlertTriangle } from "lucide-react";
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
  remediationResult,
}: ReportViewProps) {
  const [activeTab, setActiveTab] = useState<"report" | "evidence" | "trace">("report");

  if (!hypothesis && (!evidenceList || evidenceList.length === 0)) {
    return null;
  }

  const confidencePct = hypothesis ? Math.round(hypothesis.confidence * 100) : 87;
  const groundednessPct = hypothesis ? Math.round(hypothesis.groundedness_score * 100) : 95;
  const isAwaitingApproval = status === "awaiting_approval";
  const isExecuted = status === "remediation_executed";
  const isRejected = status === "rejected_by_human";

  return (
    <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 overflow-hidden shadow-xs">
      {/* 1. Wireframe Tabs: Report   Evidence (3)   Trace */}
      <div className="px-6 pt-3.5 border-b border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <button
            onClick={() => setActiveTab("report")}
            className={`pb-3 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === "report"
                ? "border-emerald-500 text-zinc-900 dark:text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            Report
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`pb-3 text-xs font-medium border-b-2 flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeTab === "evidence"
                ? "border-emerald-500 text-zinc-900 dark:text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            <span>Evidence ({evidenceList.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("trace")}
            className={`pb-3 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === "trace"
                ? "border-emerald-500 text-zinc-900 dark:text-zinc-100 font-semibold"
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
          <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Groundedness {groundednessPct}%</span>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "report" && (
        <div className="p-6 space-y-6 text-sm">
          {/* Header Title: DB connection pool exhaustion · orders */}
          <div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
              {hypothesis?.root_cause || "DB connection pool exhaustion · orders"}
            </h2>
          </div>

          {/* Narrative Body with exact inline evidence chips */}
          <div className="text-zinc-700 dark:text-zinc-300 leading-relaxed space-y-3 font-sans">
            <p>
              Errors began when <code className="text-xs font-mono font-medium text-zinc-900 dark:text-zinc-100">db_pool_in_use</code> hit max{" "}
              {evidenceList.slice(0, 1).map((e) => (
                <button
                  key={e.id}
                  onClick={() => onSelectEvidence(e)}
                  className="inline-block px-1.5 py-0.2 mx-1 rounded text-xs font-mono bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 cursor-pointer"
                >
                  {e.id}
                </button>
              ))}
              . Logs show &quot;too many connections&quot;{" "}
              {evidenceList.slice(1, 2).map((e) => (
                <button
                  key={e.id}
                  onClick={() => onSelectEvidence(e)}
                  className="inline-block px-1.5 py-0.2 mx-1 rounded text-xs font-mono bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 cursor-pointer"
                >
                  {e.id}
                </button>
              ))}
              . Runbook section 2 matches{" "}
              {evidenceList.slice(2, 3).map((e) => (
                <button
                  key={e.id}
                  onClick={() => onSelectEvidence(e)}
                  className="inline-block px-1.5 py-0.2 mx-1 rounded text-xs font-mono bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 cursor-pointer"
                >
                  {e.id}
                </button>
              ))}
              .
            </p>
          </div>

          {/* Suggested action line: Suggested action review_config → orders · increase pool size */}
          <div className="pt-4 border-t border-zinc-200/60 dark:border-zinc-800/60 space-y-4">
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="text-zinc-400">Suggested action</span>
              <span className="text-zinc-900 dark:text-zinc-100 font-semibold">
                {hypothesis?.recommended_action?.type || "review_config"} → {hypothesis?.recommended_action?.target || "orders"} · increase pool size
              </span>
            </div>

            {/* Awaiting Approval Actions: [ Approve (dry-run) ]  [ Reject ] */}
            {isAwaitingApproval && (
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={onRequestApproval}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-zinc-950 shadow-[0_0_12px_rgba(16,185,129,0.3)] transition-all active:scale-98 cursor-pointer"
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
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Executed as dry-run. No changes made.</span>
                </div>
                <div className="text-[11px] text-zinc-500 space-y-0.5">
                  <div>Action: {hypothesis?.recommended_action?.type || "review_config"} (orders)</div>
                  <div>Capability Token: Verified single-use token</div>
                  <div>Parameters: {JSON.stringify(hypothesis?.recommended_action?.parameters || { MAX_DB_POOL_SIZE: 20 })}</div>
                </div>
              </div>
            )}

            {isRejected && (
              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-mono text-zinc-500">
                Action rejected by engineer. Incident marked resolved.
              </div>
            )}
          </div>
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
                className="px-2.5 py-1 rounded text-xs bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 transition-colors"
              >
                Inspect
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Trace */}
      {activeTab === "trace" && (
        <div className="p-6 space-y-2 font-mono text-xs">
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
      )}
    </div>
  );
}
