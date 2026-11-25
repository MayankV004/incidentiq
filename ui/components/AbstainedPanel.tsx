"use client";

import React, { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Evidence, FeedbackVerdict, Hypothesis, IncidentEvent, IncidentFeedback } from "../types/api";

interface AbstainedPanelProps {
  hypothesis: Hypothesis | null;
  evidenceList?: Evidence[];
  events?: IncidentEvent[];
  feedback?: IncidentFeedback;
  onSubmitFeedback?: (verdict: FeedbackVerdict) => Promise<void>;
}

export function AbstainedPanel({
  hypothesis,
  evidenceList = [],
  events = [],
  feedback,
  onSubmitFeedback,
}: AbstainedPanelProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const confidence =
    hypothesis?.confidence !== undefined ? `${Math.round(hypothesis.confidence * 100)}%` : "—";

  const checkedNodes = Array.from(
    new Set(events.map((ev) => ev.node).filter((n) => n !== "input_guard" && n !== "output_guard"))
  );
  const checkedText =
    checkedNodes.length > 0
      ? checkedNodes.join(" · ")
      : evidenceList.length > 0
      ? `${evidenceList.length} evidence item(s) collected`
      : "No agent steps recorded";

  const rationale =
    hypothesis?.abstain_reason ||
    hypothesis?.reasoning ||
    "Insufficient corroborating evidence to publish an actionable diagnosis.";

  return (
    <div className="rounded-xl border p-6 bg-amber-500/5 dark:bg-amber-500/5 border-amber-500/30 font-mono text-xs space-y-4 shadow-xs">
      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-semibold text-sm">
        <AlertTriangle className="w-4 h-4 shrink-0" />
        <span>⚠ Diagnosis withheld (abstained due to low confidence or missing evidence).</span>
      </div>

      <div className="space-y-2.5 text-zinc-700 dark:text-zinc-300 pt-2 border-t border-amber-500/20">
        <div className="grid grid-cols-12 gap-2">
          <span className="col-span-2 text-zinc-400 font-medium">Checked</span>
          <span className="col-span-10 text-zinc-800 dark:text-zinc-200">{checkedText}</span>
        </div>

        <div className="grid grid-cols-12 gap-2">
          <span className="col-span-2 text-amber-600 dark:text-amber-400 font-medium">Reason</span>
          <span className="col-span-10 text-zinc-800 dark:text-zinc-200">{rationale}</span>
        </div>

        <div className="grid grid-cols-12 gap-2">
          <span className="col-span-2 text-zinc-400 font-medium">Evidence</span>
          <span className="col-span-10 text-zinc-800 dark:text-zinc-200">
            {evidenceList.length > 0
              ? evidenceList.map((e) => e.id).join(", ")
              : "None collected"}
          </span>
        </div>
      </div>

      <div className="pt-2 text-zinc-500 dark:text-zinc-400 border-t border-amber-500/20 flex flex-wrap items-center justify-between gap-3">
        <span>Confidence: {confidence} — safe abstention triggered</span>
        {onSubmitFeedback && (
          <div className="flex items-center gap-2">
            {feedback && (
              <span className="text-zinc-400">Saved: {feedback.verdict}</span>
            )}
            <button
              disabled={isSubmitting}
              onClick={async () => {
                setIsSubmitting(true);
                try {
                  await onSubmitFeedback("good_abstention");
                } finally {
                  setIsSubmitting(false);
                }
              }}
              className={`px-2.5 py-1 rounded border transition-colors cursor-pointer disabled:opacity-50 ${
                feedback?.verdict === "good_abstention"
                  ? "bg-lime-400/15 border-lime-500/40 text-lime-700 dark:text-lime-400 font-semibold"
                  : "border-amber-500/30 hover:bg-amber-500/10 text-zinc-700 dark:text-zinc-300"
              }`}
            >
              Good abstention
            </button>
            <button
              disabled={isSubmitting}
              onClick={async () => {
                setIsSubmitting(true);
                try {
                  await onSubmitFeedback("false_alarm");
                } finally {
                  setIsSubmitting(false);
                }
              }}
              className={`px-2.5 py-1 rounded border transition-colors cursor-pointer disabled:opacity-50 ${
                feedback?.verdict === "false_alarm"
                  ? "bg-red-500/15 border-red-500/40 text-red-700 dark:text-red-400 font-semibold"
                  : "border-amber-500/30 hover:bg-amber-500/10 text-zinc-700 dark:text-zinc-300"
              }`}
            >
              Missed outage
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
