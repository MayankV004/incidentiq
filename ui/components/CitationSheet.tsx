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
        return <Activity className="w-4 h-4 text-emerald-400" />;
      case "log":
        return <Database className="w-4 h-4 text-sky-400" />;
      case "runbook":
      case "postmortem":
        return <FileText className="w-4 h-4 text-amber-400" />;
      default:
        return <ExternalLink className="w-4 h-4 text-zinc-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-xs transition-opacity animate-fade-in">
      {/* Backdrop click to dismiss */}
      <div className="fixed inset-0" onClick={onClose} />

      {/* Drawer Panel */}
      <aside className="relative z-10 w-full max-w-lg bg-zinc-900 border-l border-zinc-800 h-full p-6 flex flex-col shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            {getSourceIcon(evidence.source)}
            <span className="font-mono text-sm font-semibold text-zinc-100">
              {evidence.id}
            </span>
            <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
              {evidence.source}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="py-6 space-y-6 flex-1">
          {/* Summary */}
          <div>
            <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-400 mb-2">
              Extracted Evidence
            </h4>
            <p className="text-sm text-zinc-200 leading-relaxed bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/60">
              {evidence.summary}
            </p>
          </div>

          {/* Raw Reference / Details */}
          {evidence.raw_ref && (
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-400 mb-2">
                Origin Reference
              </h4>
              <p className="text-xs font-mono text-zinc-400 bg-zinc-950 p-3 rounded border border-zinc-800 break-all">
                {evidence.raw_ref}
              </p>
            </div>
          )}

          {/* Raw Data Payload */}
          {evidence.data && Object.keys(evidence.data).length > 0 && (
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-400 mb-2">
                Raw Telemetry Payload
              </h4>
              <pre className="text-xs font-mono text-zinc-300 bg-zinc-950 p-3 rounded border border-zinc-800 overflow-x-auto max-h-80 leading-snug">
                {JSON.stringify(evidence.data, null, 2)}
              </pre>
            </div>
          )}

          {/* Confidence Badge */}
          {evidence.confidence !== undefined && (
            <div className="flex items-center justify-between text-xs text-zinc-400 pt-2 border-t border-zinc-800/60">
              <span>Agent Confidence Score</span>
              <span className="font-mono text-zinc-200 font-medium">
                {Math.round(evidence.confidence * 100)}%
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-zinc-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 font-medium transition-colors"
          >
            Close Sheet
          </button>
        </div>
      </aside>
    </div>
  );
}
