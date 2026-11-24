"use client";

import React from "react";
import { Server, ArrowRight } from "lucide-react";

interface ShopViewProps {
  onSwitchToLive?: () => void;
}

const SHOP_SERVICES = [
  { name: "API Gateway", port: 8001, role: "Routing, JWT, Rate Limiting" },
  { name: "Orders Service", port: 8002, role: "Cart, Checkout, DB Pool" },
  { name: "Payments Service", port: 8003, role: "Transaction Orchestrator" },
  { name: "Fake External", port: 8004, role: "Simulated Payment Provider" },
];

export function ShopView({ onSwitchToLive }: ShopViewProps) {
  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Shop Microservices Topology
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Internal Docker network services isolated from public ingress in the cost-capped demo
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {SHOP_SERVICES.map((svc) => (
          <div
            key={svc.name}
            className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 space-y-3 shadow-xs"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                {svc.name}
              </span>
              <Server className="w-3.5 h-3.5 text-zinc-400" />
            </div>

            <div className="space-y-1 font-mono text-[11px] text-zinc-500">
              <div className="flex justify-between">
                <span>Internal Port:</span>
                <span className="text-zinc-900 dark:text-zinc-200">:{svc.port}</span>
              </div>
              <div className="flex justify-between">
                <span>Exposure:</span>
                <span className="text-zinc-600 dark:text-zinc-400">Docker internal only</span>
              </div>
            </div>

            <p className="text-[11px] text-zinc-400 dark:text-zinc-500 pt-2 border-t border-zinc-100 dark:border-zinc-800">
              {svc.role}
            </p>
          </div>
        ))}
      </div>

      <div className="w-full rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
        <div className="space-y-1">
          <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-200 uppercase tracking-wider font-mono">
            Scenario Replay Control
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Remote fault injection endpoints are disabled on public ingress. Use Live Triage to replay deterministic outage scenarios cleanly.
          </p>
        </div>

        {onSwitchToLive && (
          <button
            onClick={onSwitchToLive}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-lime-400 text-zinc-950 font-sans font-semibold text-xs hover:bg-lime-300 shadow-[0_0_10px_rgba(163,230,53,0.35)] cursor-pointer shrink-0"
          >
            <span>Go to Live Triage</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
