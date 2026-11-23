"use client";

import React from "react";
import { Activity, ShieldCheck, BarChart3, Radio, Server } from "lucide-react";

export type NavTab = "live" | "incidents" | "evaluation" | "security" | "shop";

interface HeaderNavProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  isInvestigating?: boolean;
}

export function HeaderNav({ currentTab, onSelectTab, isInvestigating }: HeaderNavProps) {
  const tabs: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: "live", label: "Live Triage", icon: <Radio className="w-4 h-4" /> },
    { id: "incidents", label: "Incidents", icon: <Activity className="w-4 h-4" /> },
    { id: "evaluation", label: "Evaluation", icon: <BarChart3 className="w-4 h-4" /> },
    { id: "security", label: "Security Matrix", icon: <ShieldCheck className="w-4 h-4" /> },
    { id: "shop", label: "Shop Chaos Lab", icon: <Server className="w-4 h-4" /> },
  ];

  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded bg-zinc-100 flex items-center justify-center text-zinc-950 font-bold text-xs tracking-tighter">
            IQ
          </div>
          <span className="font-semibold text-sm tracking-tight text-zinc-100">
            IncidentIQ
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-900 text-zinc-400 border border-zinc-800">
            On-Call Copilot
          </span>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1">
          {tabs.map((tab) => {
            const isActive = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-zinc-800 text-zinc-100"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.id === "live" && isInvestigating && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Status Pill */}
        <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
          <span>Control Plane Active</span>
        </div>
      </div>
    </header>
  );
}
