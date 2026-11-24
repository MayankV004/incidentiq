"use client";

import React, { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { IncidentSummary } from "../../types/api";
import { fetchIncidents } from "../../lib/api";
import { formatCost, formatLatency } from "../../lib/utils";
import { TableRowSkeleton } from "../Skeleton";

interface IncidentsViewProps {
  onSelectIncident?: (id: string) => void;
}

export function IncidentsView({ onSelectIncident }: IncidentsViewProps) {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchIncidents();
      setIncidents(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchIncidents()
      .then((data) => {
        if (!active) return;
        setIncidents(data);
        setLoadError(null);
      })
      .catch((err) => {
        if (!active) return;
        setLoadError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
      case "remediation_executed":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-lime-400/10 text-lime-600 dark:text-lime-400 border border-lime-400/20">
            Resolved
          </span>
        );
      case "awaiting_approval":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            Awaiting Approval
          </span>
        );
      case "abstained":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
            Abstained
          </span>
        );
      case "budget_exceeded":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            Budget Exceeded
          </span>
        );
      case "failed":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
            Failed
          </span>
        );
      case "rejected_by_human":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
            Rejected
          </span>
        );
      case "running":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-lime-400/10 text-lime-600 dark:text-lime-400 border border-lime-400/20 animate-pulse">
            Investigating
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Incident History
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Audit log of autonomous agent investigations and human remediation gates
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 transition-colors shadow-2xs cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {loadError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs font-mono text-red-700 dark:text-red-300">
          Failed to load incidents: {loadError}
        </div>
      )}

      <div className="w-full rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 overflow-hidden shadow-xs">
        <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60 font-mono text-xs">
          <div className="bg-zinc-50/60 dark:bg-zinc-950/60 px-6 py-2.5 text-zinc-400 dark:text-zinc-500 text-[11px] grid grid-cols-12 gap-3 uppercase tracking-wider">
            <span className="col-span-3">Incident ID / Service</span>
            <span className="col-span-4">Symptom / Diagnosis</span>
            <span className="col-span-2">Status</span>
            <span className="col-span-1 text-right">Latency</span>
            <span className="col-span-2 text-right">Cost</span>
          </div>

          {isLoading ? (
            <>
              <TableRowSkeleton />
              <TableRowSkeleton />
              <TableRowSkeleton />
              <TableRowSkeleton />
            </>
          ) : incidents.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-zinc-400">
              No incidents recorded yet. Launch an investigation in Live Triage to generate runs.
            </div>
          ) : (
            incidents.map((inc) => (
              <div
                key={inc.incident_id}
                onClick={() => onSelectIncident?.(inc.incident_id)}
                className={`px-6 py-3.5 grid grid-cols-12 gap-3 items-center hover:bg-zinc-50 dark:hover:bg-zinc-900/40 transition-colors ${
                  onSelectIncident ? "cursor-pointer" : ""
                }`}
              >
                <div className="col-span-3">
                  <span className="text-zinc-900 dark:text-zinc-200 font-semibold block">
                    {inc.incident_id}
                  </span>
                  <span className="text-[11px] text-zinc-400 uppercase font-mono">
                    {inc.service}
                  </span>
                </div>

                <div className="col-span-4 pr-2">
                  <span className="text-zinc-800 dark:text-zinc-300 font-sans text-xs truncate block font-medium">
                    {inc.root_cause || inc.symptom}
                  </span>
                  {inc.confidence !== undefined && inc.confidence !== null && (
                    <span className="text-[10px] text-zinc-400 font-mono">
                      Confidence: {Math.round(inc.confidence * 100)}%
                    </span>
                  )}
                </div>

                <div className="col-span-2">{getStatusBadge(inc.status)}</div>

                <div className="col-span-1 text-right text-zinc-600 dark:text-zinc-400 tabular-nums">
                  {formatLatency(inc.latency_ms)}
                </div>

                <div className="col-span-2 text-right text-zinc-600 dark:text-zinc-400 tabular-nums">
                  {formatCost(inc.cost_usd)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
