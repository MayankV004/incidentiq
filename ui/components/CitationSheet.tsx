"use client";

import React, { useEffect } from "react";
import { X, ExternalLink, Database, FileText, Activity } from "lucide-react";
import { Evidence } from "../types/api";

interface CitationSheetProps {
  evidence: Evidence | null;
  onClose: () => void;
}

export function CitationSheet({ evidence, onClose }: CitationSheetProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!evidence) return null;

  const getSourceIcon = (source: string) => {
    switch (source) {
      case "metric":
        return <Activity className="w-4 h-4 text-emerald-500" />;
      case "log":
        return <Database className="w-4 h-4 text-sky-500" />;
      case "runbook":
      case "postmortem":
      case "memory":
        return <FileText className="w-4 h-4 text-amber-500" />;
      default:
        return <ExternalLink className="w-4 h-4 text-zinc-400" />;
    }
  };

  const evidenceKind = evidence.source || evidence.kind || "evidence";

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in">
      {/* Backdrop */}
      <div className="fixed inset-0" onClick={onClose} />

      {/* Drawer */}
      <aside className="relative z-10 w-full max-w-lg bg-white dark:bg-[#121215] border-l border-zinc-200 dark:border-zinc-800 h-full p-6 flex flex-col shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-zinc-200/80 dark:border-zinc-800/80">
          <div className="flex items-center gap-2">
            {getSourceIcon(evidenceKind)}
            <span className="font-mono text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              {evidence.id}
            </span>
            <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
              {evidenceKind}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="py-6 space-y-6 flex-1">
          <div>
            <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-2 font-mono">
              Extracted Evidence
            </h4>
            <p className="text-sm text-zinc-800 dark:text-zinc-200 leading-relaxed bg-zinc-50 dark:bg-zinc-950 p-3.5 rounded-lg border border-zinc-200/80 dark:border-zinc-800/80">
              {evidence.summary}
            </p>
          </div>

          {evidence.raw_ref && (
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-2 font-mono">
                Origin Reference
              </h4>
              <p className="text-xs font-mono text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-950 p-3 rounded border border-zinc-200/80 dark:border-zinc-800/80 break-all">
                {evidence.raw_ref}
              </p>
            </div>
          )}

          {evidence.data && Object.keys(evidence.data).length > 0 && (
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-2 font-mono">
                Raw Telemetry Payload
              </h4>
              <pre className="text-xs font-mono text-zinc-700 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-950 p-3 rounded border border-zinc-200/80 dark:border-zinc-800/80 overflow-x-auto max-h-80 leading-snug">
                {JSON.stringify(evidence.data, null, 2)}
              </pre>
            </div>
          )}

          {evidence.confidence !== undefined && (
            <div className="flex items-center justify-between text-xs text-zinc-500 pt-2 border-t border-zinc-200/80 dark:border-zinc-800/60 font-mono">
              <span>Agent Confidence Score</span>
              <span className="text-zinc-900 dark:text-zinc-200 font-semibold">
                {Math.round(evidence.confidence * 100)}%
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-zinc-200/80 dark:border-zinc-800/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-xs text-zinc-800 dark:text-zinc-200 font-medium transition-colors cursor-pointer"
          >
            Close Sheet
          </button>
        </div>
      </aside>
    </div>
  );
}
