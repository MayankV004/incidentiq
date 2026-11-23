"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  FileText,
  Activity,
  Terminal,
  Clock,
  Layers,
} from "lucide-react";
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

  const confidencePct = hypothesis ? Math.round(hypothesis.confidence * 100) : 0;
  const groundednessPct = hypothesis ? Math.round(hypothesis.groundedness_score * 100) : 0;
  const isAwaitingApproval = status === "awaiting_approval";
  const isExecuted = status === "remediation_executed";
  const isRejected = status === "rejected_by_human";

  return (
    <div className="bg-zinc-900 border border-zinc-800/80 rounded-xl overflow-hidden shadow-sm">
      {/* Sub-tabs Header */}
      <div className="px-5 pt-3 border-b border-zinc-800/80 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setActiveTab("report")}
            className={`pb-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "report"
                ? "border-zinc-100 text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Triage Report
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`pb-3 text-xs font-medium border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === "evidence"
                ? "border-zinc-100 text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span>Evidence</span>
            <span className="px-1.5 py-0.2 rounded-full bg-zinc-800 text-[10px] font-mono text-zinc-300">
              {evidenceList.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("trace")}
            className={`pb-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "trace"
                ? "border-zinc-100 text-zinc-100 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Execution Trace
          </button>
        </div>

        {/* Live Groundedness & Confidence Badges */}
        <div className="flex items-center gap-3 pb-3">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-mono">
            <span>Confidence:</span>
            <span className="font-semibold text-zinc-100">{confidencePct}%</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Groundedness: {groundednessPct}%</span>
          </div>
        </div>
      </div>

      {/* Tab 1: Triage Report */}
      {activeTab === "report" && (
        <div className="p-6 space-y-6">
          {/* Root-Cause Banner */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
                Primary Root Cause
              </span>
              <span className="text-zinc-600">·</span>
              <span className="text-xs font-mono text-zinc-300 uppercase">
                {incident?.alert?.service || "orders"}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-zinc-100 tracking-tight">
              {hypothesis?.root_cause || "Analyzing incident telemetry..."}
            </h2>
          </div>

          {/* Narrative with Evidence Chips */}
          <div className="bg-zinc-950/70 p-4 rounded-lg border border-zinc-800/60 text-sm text-zinc-300 leading-relaxed space-y-3">
            <p>
              Telemetry across metrics and logs indicates service degradation on{" "}
              <strong className="text-zinc-100 font-mono font-medium">
                {incident?.alert?.service}
              </strong>
              . Correlation with historical runbooks corroborates resource exhaustion.
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-zinc-800/60">
              <span className="text-xs text-zinc-400">Supporting Citations:</span>
              {evidenceList.map((e) => (
                <button
                  key={e.id}
                  onClick={() => onSelectEvidence(e)}
                  className="px-2 py-0.5 rounded text-xs font-mono bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition-colors cursor-pointer inline-flex items-center gap-1"
                >
                  <span>[{e.id}]</span>
                  <span className="text-[10px] text-zinc-400 uppercase">{e.source}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Remediation Action Card */}
          {hypothesis?.recommended_action && (
            <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                  Recommended Remediation
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                  MCP Tool: {hypothesis.recommended_action.type}
                </span>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono text-zinc-200">
                <Terminal className="w-3.5 h-3.5 text-zinc-400" />
                <span>Target:</span>
                <span className="text-zinc-100 font-semibold">
                  {hypothesis.recommended_action.target}
                </span>
                {hypothesis.recommended_action.parameters && (
                  <span className="text-zinc-400">
                    ({JSON.stringify(hypothesis.recommended_action.parameters)})
                  </span>
                )}
              </div>

              {/* Approval Buttons */}
              {isAwaitingApproval && (
                <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-amber-400 font-mono">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Awaiting authorization from engineer</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={onReject}
                      className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
                    >
                      Reject
                    </button>
                    <button
                      onClick={onRequestApproval}
                      className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-zinc-100 text-zinc-950 hover:bg-white active:scale-98 transition-all"
                    >
                      Approve (dry-run)
                    </button>
                  </div>
                </div>
              )}

              {/* Executed Receipt */}
              {isExecuted && (
                <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-2 text-xs text-emerald-400 font-mono bg-emerald-500/5 p-2 rounded border border-emerald-500/20">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>
                    Executed as dry-run. No destructive changes made. Verification receipt recorded.
                  </span>
                </div>
              )}

              {/* Rejected Notice */}
              {isRejected && (
                <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-2 text-xs text-zinc-400 font-mono bg-zinc-900 p-2 rounded border border-zinc-800">
                  <span className="w-2 h-2 rounded-full bg-zinc-500" />
                  <span>Remediation action declined by engineer. Incident marked closed.</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Evidence List */}
      {activeTab === "evidence" && (
        <div className="p-6 divide-y divide-zinc-800/60">
          {evidenceList.map((ev) => (
            <div
              key={ev.id}
              className="py-3.5 flex items-start justify-between gap-4 first:pt-0 last:pb-0"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-zinc-200">
                    [{ev.id}]
                  </span>
                  <span className="text-[10px] uppercase font-mono px-2 py-0.2 rounded bg-zinc-800 text-zinc-400">
                    {ev.source}
                  </span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">{ev.summary}</p>
              </div>

              <button
                onClick={() => onSelectEvidence(ev)}
                className="px-2.5 py-1 rounded text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors shrink-0"
              >
                Inspect
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Execution Trace */}
      {activeTab === "trace" && (
        <div className="p-6 space-y-3 font-mono text-xs">
          <div className="text-zinc-500 pb-2 border-b border-zinc-800 flex justify-between">
            <span>EVENT / NODE</span>
            <span>SUMMARY</span>
          </div>
          {(incident?.events || []).map((ev, i) => (
            <div
              key={ev.id || i}
              className="flex items-start justify-between py-1.5 border-b border-zinc-800/40 text-zinc-300"
            >
              <div className="flex items-center gap-2 min-w-[180px]">
                <span className="text-zinc-500">{i + 1}.</span>
                <span className="text-zinc-100 font-semibold">{ev.node}</span>
              </div>
              <div className="text-right text-zinc-400 truncate max-w-md">
                {ev.summary}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
