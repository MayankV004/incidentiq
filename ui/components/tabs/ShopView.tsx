"use client";

import React, { useState } from "react";
import { Server, Zap, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";

interface ShopViewProps {
  onSwitchToLive?: () => void;
}

export function ShopView({ onSwitchToLive }: ShopViewProps) {
  const [activeFault, setActiveFault] = useState<string | null>(null);
  const [isInjecting, setIsInjecting] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  const services = [
    { name: "API Gateway", port: 8001, status: "healthy", role: "Routing, JWT, Rate Limiting" },
    { name: "Orders Service", port: 8002, status: activeFault?.includes("db") ? "degraded" : "healthy", role: "Cart, Checkout, DB Pool" },
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">
            Shop Microservices & Chaos Control Plane
          </h2>
          <p className="text-xs text-zinc-400">
            Simulate production outages in the e-commerce shop and observe IncidentIQ triage the failure live
          </p>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-100">{svc.name}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  svc.status === "healthy"
                    ? "bg-emerald-400"
                    : svc.status === "degraded"
                    ? "bg-amber-400 animate-ping"
                    : "bg-sky-400 animate-pulse"
                }`}
              />
            </div>

            <div className="space-y-1 font-mono text-[11px] text-zinc-400">
              <div className="flex justify-between">
                <span>Port:</span>
                <span className="text-zinc-200">:{svc.port}</span>
              </div>
              <div className="flex justify-between">
                <span>Status:</span>
                <span
                  className={
                    svc.status === "healthy"
                      ? "text-emerald-400"
                      : "text-amber-400 font-semibold uppercase"
                  }
                >
                  {svc.status}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-zinc-500 pt-2 border-t border-zinc-800">
              {svc.role}
            </p>
          </div>
        ))}
      </div>

      {/* Chaos Injection Controls */}
      <div className="bg-zinc-900 border border-zinc-800/80 rounded-xl p-6 space-y-4">
        <h3 className="text-xs font-semibold text-zinc-100 uppercase tracking-wider">
          Chaos Fault Injectors
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            onClick={() => handleInject("db_pool", "Orders DB Pool Exhaustion")}
            disabled={isInjecting}
            className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-amber-500/50 text-left transition-all group"
          >
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-200 group-hover:text-amber-400">
              <span>Orders: DB Pool Exhaust</span>
              <Zap className="w-3.5 h-3.5 text-zinc-500 group-hover:text-amber-400" />
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">
              Pins max pool connections to trigger connection acquisition timeouts
            </p>
          </button>

          <button
            onClick={() => handleInject("slow_query", "Orders Slow DB Query")}
            disabled={isInjecting}
            className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-amber-500/50 text-left transition-all group"
          >
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-200 group-hover:text-amber-400">
              <span>Orders: Slow Query (4.2s)</span>
              <Zap className="w-3.5 h-3.5 text-zinc-500 group-hover:text-amber-400" />
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">
              Forces table scan on unindexed checkout table, driving p95 above SLA
            </p>
          </button>

          <button
            onClick={() => handleInject("delay", "Fake External 6s Latency")}
            disabled={isInjecting}
            className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-amber-500/50 text-left transition-all group"
          >
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-200 group-hover:text-amber-400">
              <span>Payments: Gateway Timeout</span>
              <Zap className="w-3.5 h-3.5 text-zinc-500 group-hover:text-amber-400" />
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">
              Injects 6.0s delay in external payment gateway, causing client timeouts
            </p>
          </button>
        </div>

        {/* Status / Feedback message */}
        {message && (
          <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between text-xs font-mono text-zinc-300">
            <span>{message}</span>
            {activeFault && onSwitchToLive && (
              <button
                onClick={onSwitchToLive}
                className="px-3 py-1 rounded bg-zinc-100 text-zinc-950 font-sans font-semibold text-xs hover:bg-white"
              >
                Go to Live Triage →
              </button>
            )}
          </div>
        )}

        <div className="pt-2 flex justify-end">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset All Chaos to Baseline</span>
          </button>
        </div>
      </div>
    </div>
  );
}
