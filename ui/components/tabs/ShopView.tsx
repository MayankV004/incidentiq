"use client";

import React, { useState } from "react";
import { Zap, RefreshCw } from "lucide-react";

interface ShopViewProps {
  onSwitchToLive?: () => void;
}

export function ShopView({ onSwitchToLive }: ShopViewProps) {
  const [activeFault, setActiveFault] = useState<string | null>(null);
  const [isInjecting, setIsInjecting] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  const services = [
    { name: "API Gateway", port: 8001, status: "healthy", role: "Routing, JWT, Rate Limiting" },
    { name: "Orders Service", port: 8002, status: activeFault?.includes("db") || activeFault?.includes("query") ? "degraded" : "healthy", role: "Cart, Checkout, DB Pool" },
    { name: "Payments Service", port: 8003, status: activeFault?.includes("delay") ? "degraded" : "healthy", role: "Transaction Orchestrator" },
    { name: "Fake External", port: 8004, status: activeFault?.includes("delay") ? "slow" : "healthy", role: "Simulated Visa/Stripe API" },
  ];

  const handleInject = (faultType: string, label: string) => {
    setIsInjecting(true);
    setActiveFault(faultType);
    setMessage(`Injected: ${label}. Shop services now experiencing simulated degradation.`);
    setIsInjecting(false);
  };

  const handleReset = () => {
    setIsInjecting(true);
    setActiveFault(null);
    setMessage("All chaos injection cleared. Shop services restored to healthy baseline.");
    setIsInjecting(false);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Shop Microservices & Chaos Control Plane
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Simulate production outages in the e-commerce shop and observe IncidentIQ triage the failure live
          </p>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 space-y-3 shadow-xs"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">{svc.name}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  svc.status === "healthy"
                    ? "bg-emerald-500 shadow-[0_0_6px_#10b981]"
                    : svc.status === "degraded"
                    ? "bg-amber-500 animate-ping"
                    : "bg-sky-500 animate-pulse"
                }`}
              />
            </div>

            <div className="space-y-1 font-mono text-[11px] text-zinc-500">
              <div className="flex justify-between">
                <span>Port:</span>
                <span className="text-zinc-900 dark:text-zinc-200">:{svc.port}</span>
              </div>
              <div className="flex justify-between">
                <span>Status:</span>
                <span
                  className={
                    svc.status === "healthy"
                      ? "text-emerald-600 dark:text-emerald-400 font-medium"
                      : "text-amber-600 dark:text-amber-400 font-semibold uppercase"
                  }
                >
                  {svc.status}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-zinc-400 dark:text-zinc-500 pt-2 border-t border-zinc-100 dark:border-zinc-800">
              {svc.role}
            </p>
          </div>
        ))}
      </div>

      {/* Chaos Injection Controls */}
      <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-6 space-y-4 shadow-xs">
        <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-200 uppercase tracking-wider font-mono">
          Chaos Fault Injectors
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            onClick={() => handleInject("db_pool", "Orders DB Pool Exhaustion")}
            disabled={isInjecting}
            className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 text-left transition-all group cursor-pointer"
          >
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-900 dark:text-zinc-200 group-hover:text-emerald-600 dark:group-hover:text-emerald-400">
              <span>Orders: DB Pool Exhaust</span>
              <Zap className="w-3.5 h-3.5 text-zinc-400 group-hover:text-emerald-500" />
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">
              Pins max pool connections to trigger connection acquisition timeouts
            </p>
          </button>

          <button
            onClick={() => handleInject("slow_query", "Orders Slow DB Query")}
            disabled={isInjecting}
            className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 text-left transition-all group cursor-pointer"
          >
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-900 dark:text-zinc-200 group-hover:text-emerald-600 dark:group-hover:text-emerald-400">
              <span>Orders: Slow Query (4.2s)</span>
              <Zap className="w-3.5 h-3.5 text-zinc-400 group-hover:text-emerald-500" />
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">
              Forces table scan on unindexed checkout table, driving p95 above SLA
            </p>
          </button>

          <button
            onClick={() => handleInject("delay", "Fake External 6s Latency")}
            disabled={isInjecting}
            className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 text-left transition-all group cursor-pointer"
          >
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-900 dark:text-zinc-200 group-hover:text-emerald-600 dark:group-hover:text-emerald-400">
              <span>Payments: Gateway Timeout</span>
              <Zap className="w-3.5 h-3.5 text-zinc-400 group-hover:text-emerald-500" />
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">
              Injects 6.0s delay in external payment gateway, causing client timeouts
            </p>
          </button>
        </div>

        {message && (
          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-xs font-mono text-zinc-700 dark:text-zinc-300">
            <span>{message}</span>
            {activeFault && onSwitchToLive && (
              <button
                onClick={onSwitchToLive}
                className="px-3 py-1 rounded bg-emerald-500 text-zinc-950 font-sans font-semibold text-xs hover:bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.3)] cursor-pointer"
              >
                Go to Live Triage →
              </button>
            )}
          </div>
        )}

        <div className="pt-2 flex justify-end">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset All Chaos to Baseline</span>
          </button>
        </div>
      </div>
    </div>
  );
}
