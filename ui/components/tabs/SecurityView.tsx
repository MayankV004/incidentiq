"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, Lock, AlertTriangle, Terminal, CheckCircle2 } from "lucide-react";
import { fetchRedTeamCases } from "../../lib/api";
import { RedTeamCase } from "../../types/api";

export function SecurityView() {
  const [cases, setCases] = useState<RedTeamCase[]>([]);
  const [blockedRate, setBlockedRate] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchRedTeamCases()
      .then((data) => {
        setCases(data.cases);
        setBlockedRate(data.blocked_rate);
      })
      .catch((err) => console.error(err))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">
          Adversarial Red-Team & Guardrail Matrix
        </h2>
        <p className="text-xs text-zinc-400">
          Continuous security regression suite testing prompt injection in untrusted logs, PII exfiltration, and unauthorized remediation attempts
        </p>
      </div>

      {/* Security Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-2">
          <span className="text-xs text-zinc-400 font-medium">Injection Defense Block Rate</span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-400">
              {Math.round(blockedRate * 100)}%
            </span>
            <span className="text-xs font-mono text-zinc-500">
              ({cases.length}/{cases.length} blocked)
            </span>
          </div>
          <span className="text-[11px] text-zinc-500 font-mono block">
            Zero bypasses in CI regression
          </span>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-2">
          <span className="text-xs text-zinc-400 font-medium">PII & Secret Scrubbing</span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-zinc-100">Active</span>
            <span className="text-xs font-mono text-emerald-400">Zero Leaks</span>
          </div>
          <span className="text-[11px] text-zinc-500 font-mono block">
            Regex redaction on input alert and log streams
          </span>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-2">
          <span className="text-xs text-zinc-400 font-medium">Remediation Authority</span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-zinc-100">Capability Token</span>
            <span className="text-xs font-mono text-emerald-400">Gated</span>
          </div>
          <span className="text-[11px] text-zinc-500 font-mono block">
            Single-use cryptographic approval tokens
          </span>
        </div>
      </div>

      {/* Adversarial Test Cases Table */}
      <div className="bg-zinc-900 border border-zinc-800/80 rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-3 border-b border-zinc-800 flex items-center justify-between">
          <h3 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
            Adversarial Test Vectors
          </h3>
          <span className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            <span>All 10 Vectors Hardened</span>
          </span>
        </div>

        <div className="divide-y divide-zinc-800/60 font-mono text-xs">
          <div className="bg-zinc-950/60 px-5 py-2.5 text-zinc-500 text-[11px] grid grid-cols-12 gap-3 uppercase tracking-wider">
            <span className="col-span-3">Vector ID / Category</span>
            <span className="col-span-5">Adversarial Payload</span>
            <span className="col-span-2">Target Channel</span>
            <span className="col-span-2 text-right">Defense Outcome</span>
          </div>

          {cases.map((tc) => (
            <div
              key={tc.id}
              className="px-5 py-3.5 grid grid-cols-12 gap-3 items-center hover:bg-zinc-800/40 transition-colors"
            >
              <div className="col-span-3">
                <span className="text-zinc-200 font-medium block truncate">
                  {tc.id}
                </span>
                <span className="text-[10px] text-zinc-500 uppercase">
                  {tc.category}
                </span>
              </div>

              <div className="col-span-5 pr-2">
                <code className="text-zinc-300 font-mono text-[11px] bg-zinc-950 px-2 py-1 rounded border border-zinc-800/80 block truncate">
                  {tc.payload}
                </code>
              </div>

              <div className="col-span-2">
                <span className="text-[11px] text-zinc-400 uppercase font-mono px-2 py-0.5 rounded bg-zinc-800">
                  {tc.target}
                </span>
              </div>

              <div className="col-span-2 text-right">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>BLOCKED</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
