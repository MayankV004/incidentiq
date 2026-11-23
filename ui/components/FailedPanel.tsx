"use client";

import React from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";

interface FailedPanelProps {
  error?: string;
  onRetry: () => void;
}

export function FailedPanel({ error, onRetry }: FailedPanelProps) {
  return (
    <div className="bg-zinc-900 border border-rose-500/30 rounded-xl p-6 shadow-sm space-y-4">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertOctagon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-zinc-100">
            Investigation Failed or Budget Exceeded
          </h3>
          <p className="text-xs text-rose-300/80 mt-0.5">
            The agent encountered an unrecoverable exception or exceeded safe execution limits
          </p>
        </div>
      </div>

      <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 text-xs font-mono text-zinc-300">
        <p className="text-rose-300">
          {error || "Process terminated abnormally. Check API server logs."}
        </p>
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-zinc-100 text-zinc-950 hover:bg-white active:scale-98 transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Retry Investigation</span>
        </button>
      </div>
    </div>
  );
}
