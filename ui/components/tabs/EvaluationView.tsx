"use client";

import React, { useEffect, useState } from "react";
import { fetchEvalResults } from "../../lib/api";
import { formatCost, formatLatency } from "../../lib/utils";
import { EvalRunMetrics } from "../../types/api";
import { MetricCardSkeleton } from "../Skeleton";

interface NormalizedEvalMetrics {
  name: string;
  accuracy_pct: number | null;
  groundedness_pct: number | null;
  abstention_pct: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  total_runs: number | null;
  simulated: boolean;
}

function normalize(name: string, raw?: EvalRunMetrics): NormalizedEvalMetrics | null {
  if (!raw) return null;
  return {
    name,
    accuracy_pct:
      raw.accuracy_pct ?? (raw.accuracy !== undefined ? raw.accuracy * 100 : null),
    groundedness_pct:
      raw.groundedness_pct ??
      (raw.groundedness_pass_rate !== undefined ? raw.groundedness_pass_rate * 100 : null),
    abstention_pct:
      raw.abstention_correct_pct ??
      (raw.abstention_precision !== undefined ? raw.abstention_precision * 100 : null),
    cost_usd: raw.mean_cost_usd ?? raw.avg_cost_usd ?? null,
    latency_ms: raw.latency_p50_ms ?? raw.avg_latency_ms ?? null,
    total_runs: raw.total_runs ?? null,
    simulated: Boolean(raw.simulated),
  };
}

function formatPct(val: number | null): string {
  return val === null ? "—" : `${Math.round(val)}%`;
}

export function EvaluationView() {
  const [evalData, setEvalData] = useState<Record<string, EvalRunMetrics>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetchEvalResults()
      .then((data) => {
        setEvalData(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : String(err)))
      .finally(() => setIsLoading(false));
  }, []);

  const runNames = Object.keys(evalData);
  const runs = runNames
    .map((name) => normalize(name, evalData[name]))
    .filter((r): r is NormalizedEvalMetrics => r !== null);

  const primary =
    normalize("v2-live", evalData["v2-live"]) ||
    normalize("v2-optimized", evalData["v2-optimized"]) ||
    runs[0] ||
    null;

  return (
    <div className="w-full space-y-6">
      <div>
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          Evaluation & Benchmark Scorecard
        </h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Results loaded directly from committed benchmark JSON artifacts via /v1/evals
        </p>
      </div>

      {loadError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs font-mono text-red-700 dark:text-red-300">
          Failed to load evaluations: {loadError}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCardSkeleton />
          <MetricCardSkeleton />
          <MetricCardSkeleton />
          <MetricCardSkeleton />
        </div>
      ) : !primary ? (
        <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-12 text-center font-mono text-xs text-zinc-500">
          No evaluation runs recorded in /v1/evals yet.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 space-y-2 shadow-xs">
              <span className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">
                Diagnostic Accuracy
              </span>
              <div className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
                {formatPct(primary.accuracy_pct)}
              </div>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500 font-mono block">
                {primary.name} ({primary.simulated ? "simulated" : "measured"})
              </span>
            </div>

            <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 space-y-2 shadow-xs">
              <span className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">
                Groundedness Pass Rate
              </span>
              <div className="text-2xl font-bold font-mono text-lime-600 dark:text-lime-400">
                {formatPct(primary.groundedness_pct)}
              </div>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500 font-mono block">
                Total runs: {primary.total_runs ?? "—"}
              </span>
            </div>

            <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 space-y-2 shadow-xs">
              <span className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">
                Honest Abstention
              </span>
              <div className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
                {formatPct(primary.abstention_pct)}
              </div>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500 font-mono block">
                Abstention correctness
              </span>
            </div>

            <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 space-y-2 shadow-xs">
              <span className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">
                Mean Cost per Incident
              </span>
              <div className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
                {primary.cost_usd !== null ? formatCost(primary.cost_usd) : "—"}
              </div>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500 font-mono block">
                p50 Latency:{" "}
                {primary.latency_ms !== null ? formatLatency(primary.latency_ms) : "—"} (
                {primary.simulated ? "simulated" : "measured"})
              </span>
            </div>
          </div>

          <div className="w-full rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 overflow-hidden shadow-xs">
            <div className="px-6 py-3 border-b border-zinc-200/80 dark:border-zinc-800 flex items-center justify-between">
              <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-200 uppercase tracking-wider font-mono">
                Recorded Evaluation Runs ({runs.length})
              </h3>
            </div>

            <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60 font-mono text-xs">
              <div className="bg-zinc-50/60 dark:bg-zinc-950/60 px-6 py-2.5 text-zinc-400 dark:text-zinc-500 text-[11px] grid grid-cols-12 gap-4 uppercase tracking-wider">
                <span className="col-span-3">Run</span>
                <span className="col-span-2">Accuracy</span>
                <span className="col-span-2">Groundedness</span>
                <span className="col-span-2">Abstention</span>
                <span className="col-span-1 text-right">Latency</span>
                <span className="col-span-2 text-right">Mean Cost</span>
              </div>

              {runs.map((r) => (
                <div key={r.name} className="px-6 py-3.5 grid grid-cols-12 gap-4 items-center">
                  <span className="col-span-3 text-zinc-900 dark:text-zinc-200 font-semibold truncate">
                    {r.name}{" "}
                    <span className="text-[10px] text-zinc-400 font-normal">
                      ({r.simulated ? "sim" : "live"}, n={r.total_runs ?? "?"})
                    </span>
                  </span>
                  <span className="col-span-2">{formatPct(r.accuracy_pct)}</span>
                  <span className="col-span-2">{formatPct(r.groundedness_pct)}</span>
                  <span className="col-span-2">{formatPct(r.abstention_pct)}</span>
                  <span className="col-span-1 text-right">
                    {r.latency_ms !== null ? formatLatency(r.latency_ms) : "—"}
                  </span>
                  <span className="col-span-2 text-right">
                    {r.cost_usd !== null ? formatCost(r.cost_usd) : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
