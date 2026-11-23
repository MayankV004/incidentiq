"use client";

import React from "react";
import { AlertTriangle, HelpCircle, Check, X } from "lucide-react";
import { Hypothesis } from "../types/api";

interface AbstainedPanelProps {
  hypothesis: Hypothesis | null;
}

export function AbstainedPanel({ hypothesis }: AbstainedPanelProps) {
  const confidence = hypothesis ? Math.round(hypothesis.confidence * 100) : 0;
  const reason = hypothesis?.abstain_reason || "Confidence below 50% threshold or conflicting observability signals.";

  return (
    <div className="bg-zinc-900 border border-amber-500/30 rounded-xl p-6 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-zinc-100">
            Investigation Abstained (Honest Uncertainty)
          </h3>
          <p className="text-xs text-amber-300/80 mt-0.5">
            Agent withheld root-cause assertion to prevent hallucinated remediation
          </p>
        </div>
      </div>

      {/* Explanation */}
      <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-zinc-400">Calculated Confidence</span>
          <span className="font-mono text-amber-400 font-semibold">{confidence}% (Required: ≥ 50%)</span>
        </div>

        <div className="pt-2 border-t border-zinc-800/80">
          <span className="text-xs text-zinc-400 block mb-1">Reason for Withholding</span>
          <p className="text-xs text-zinc-300 leading-relaxed font-mono">
            {reason}
          </p>
        </div>
      </div>

      {/* Observability Checklist */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="p-3 bg-zinc-950 rounded border border-zinc-800/80 space-y-1.5">
          <span className="text-zinc-400 font-medium block">Checked Signals</span>
          <div className="flex items-center gap-1.5 text-zinc-300">
            <Check className="w-3.5 h-3.5 text-emerald-400" />
            <span>Prometheus metrics scanned</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-300">
            <Check className="w-3.5 h-3.5 text-emerald-400" />
            <span>Application logs clustered</span>
          </div>
        </div>

        <div className="p-3 bg-zinc-950 rounded border border-zinc-800/80 space-y-1.5">
          <span className="text-zinc-400 font-medium block">Missing or Conflicting</span>
          <div className="flex items-center gap-1.5 text-amber-300">
            <X className="w-3.5 h-3.5 text-amber-400" />
            <span>Zero corroborating error spikes</span>
          </div>
          <div className="flex items-center gap-1.5 text-amber-300">
            <X className="w-3.5 h-3.5 text-amber-400" />
            <span>Runbook similarity below threshold</span>
          </div>
        </div>
      </div>
    </div>
  );
}
