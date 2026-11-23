"use client";

import React, { useEffect, useState } from "react";
import { Clock, DollarSign, RefreshCw, Activity, ArrowUpRight } from "lucide-react";
import { IncidentSummary } from "../../types/api";
import { fetchIncidents } from "../../lib/api";
import { formatCost, formatLatency } from "../../lib/utils";

interface IncidentsViewProps {
  onSelectIncident?: (id: string) => void;
}

export function IncidentsView({ onSelectIncident }: IncidentsViewProps) {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const data = await fetchIncidents();
      setIncidents(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
      case "remediation_executed":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Resolved
          </span>
        );
      case "awaiting_approval":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Awaiting Approval
          </span>
        );
      case "abstained":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
            Abstained
          </span>
        );
      case "running":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse">
            Investigating
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-800 text-zinc-400">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">Incident History</h2>
          <p className="text-xs text-zinc-400">
            Audit log of autonomous agent investigations and human remediation gates
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="bg-zinc-900 border border-zinc-800/80 rounded-xl overflow-hidden shadow-sm">
        {incidents.length === 0 ? (
          <div className="p-12 text-center text-xs text-zinc-500">
            No incidents recorded yet. Launch an investigation in Live Triage to generate runs.
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/60 font-mono text-xs">
            <div className="bg-zinc-950/60 px-5 py-2.5 text-zinc-500 text-[11px] grid grid-cols-12 gap-3 uppercase tracking-wider">
              <span className="col-span-3">Incident ID / Service</span>
              <span className="col-span-4">Symptom / Diagnosis</span>
              <span className="col-span-2">Status</span>
              <span className="col-span-1 text-right">Latency</span>
              <span className="col-span-2 text-right">Cost</span>
            </div>

            {incidents.map((inc) => (
              <div
                key={inc.incident_id}
                className="px-5 py-3.5 grid grid-cols-12 gap-3 items-center hover:bg-zinc-800/40 transition-colors"
              >
                <div className="col-span-3">
                  <span className="text-zinc-200 font-medium block">
                    {inc.incident_id}
                  </span>
                  <span className="text-[11px] text-zinc-500 uppercase">
                    {inc.service}
                  </span>
                </div>

                <div className="col-span-4 pr-2">
                  <span className="text-zinc-300 font-sans text-xs truncate block font-medium">
                    {inc.root_cause || inc.symptom}
                  </span>
                  {inc.confidence && (
                    <span className="text-[10px] text-zinc-500 font-mono">
                      Confidence: {Math.round(inc.confidence * 100)}%
                    </span>
                  )}
                </div>

                <div className="col-span-2">{getStatusBadge(inc.status)}</div>

                <div className="col-span-1 text-right text-zinc-400 tabular-nums">
                  {formatLatency(inc.latency_ms)}
                </div>

                <div className="col-span-2 text-right text-zinc-400 tabular-nums">
                  {formatCost(inc.cost_usd)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
