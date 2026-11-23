"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { Hypothesis } from "../types/api";

interface AbstainedPanelProps {
  hypothesis: Hypothesis | null;
}

export function AbstainedPanel({ hypothesis }: AbstainedPanelProps) {
  const confidence = hypothesis ? Math.round(hypothesis.confidence * 100) : 38;

  return (
    <div className="rounded-xl border p-6 bg-amber-500/5 dark:bg-amber-500/5 border-amber-500/30 font-mono text-xs space-y-4 shadow-xs">
      {/* Title */}
      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-semibold text-sm">
        <AlertTriangle className="w-4 h-4 shrink-0" />
        <span>⚠ Not confident. Here is what was checked and what is missing.</span>
      </div>

      {/* Checked vs Missing */}
      <div className="space-y-2.5 text-zinc-700 dark:text-zinc-300 pt-2 border-t border-amber-500/20">
        <div className="grid grid-cols-12 gap-2">
          <span className="col-span-2 text-zinc-400 font-medium">Checked</span>
          <span className="col-span-10 text-zinc-800 dark:text-zinc-200">
            metrics · logs · runbooks
          </span>
        </div>

        <div className="grid grid-cols-12 gap-2">
          <span className="col-span-2 text-amber-600 dark:text-amber-400 font-medium">Missing</span>
          <span className="col-span-10 text-zinc-800 dark:text-zinc-200">
            no log evidence · metrics conflict with each other
          </span>
        </div>
      </div>

      {/* Withheld reason */}
      <div className="pt-2 text-zinc-500 dark:text-zinc-400 border-t border-amber-500/20">
        Best guess withheld (confidence {confidence}%, below threshold 50%)
      </div>
    </div>
  );
}
