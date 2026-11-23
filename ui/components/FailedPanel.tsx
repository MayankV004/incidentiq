"use client";

import React from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";
import { Evidence } from "../types/api";

interface FailedPanelProps {
  error?: string;
  partialEvidence?: Evidence[];
  onRetry: () => void;
}

export function FailedPanel({
  error,
  partialEvidence = [],
  onRetry,
}: FailedPanelProps) {
  return (
    <div className="rounded-xl border p-6 bg-rose-500/5 dark:bg-rose-500/5 border-rose-500/30 font-mono text-xs space-y-4 shadow-xs">
      <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-semibold text-sm">
        <AlertOctagon className="w-4 h-4 shrink-0" />
        <span>Failed or budget exceeded</span>
      </div>

      <div className="space-y-2 text-zinc-700 dark:text-zinc-300 pt-2 border-t border-rose-500/20">
        <div className="grid grid-cols-12 gap-2">
          <span className="col-span-2 text-zinc-400 font-medium">Reason</span>
          <span className="col-span-10 text-rose-600 dark:text-rose-400 font-semibold">
            {error || "Budget limit reached at step 9"}
          </span>
        </div>

        {partialEvidence.length > 0 && (
          <div className="grid grid-cols-12 gap-2">
            <span className="col-span-2 text-zinc-400 font-medium">Partial</span>
            <span className="col-span-10 text-zinc-700 dark:text-zinc-300">
              {partialEvidence.map((e) => e.id).join(", ")}
            </span>
          </div>
        )}
      </div>

      <div className="flex justify-end pt-3 border-t border-rose-500/20">
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-950 transition-all active:scale-98 cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Retry Investigation</span>
        </button>
      </div>
    </div>
  );
}
