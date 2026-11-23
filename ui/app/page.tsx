"use client";

import React, { useEffect, useState } from "react";
import { HeaderNav, NavTab } from "../components/HeaderNav";
import { LiveView } from "../components/tabs/LiveView";
import { IncidentsView } from "../components/tabs/IncidentsView";
import { EvaluationView } from "../components/tabs/EvaluationView";
import { SecurityView } from "../components/tabs/SecurityView";
import { ShopView } from "../components/tabs/ShopView";
import { Scenario } from "../types/api";
import { fetchScenarios } from "../lib/api";

export default function Home() {
  const [currentTab, setCurrentTab] = useState<NavTab>("live");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(true);

  useEffect(() => {
    fetchScenarios()
      .then((data) => setScenarios(data))
      .catch((err) => console.error("Error loading scenarios:", err))
      .finally(() => setIsLoadingScenarios(false));
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col selection:bg-zinc-800 selection:text-zinc-100">
      {/* Top Instrument Header */}
      <HeaderNav currentTab={currentTab} onSelectTab={setCurrentTab} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {currentTab === "live" && (
          <LiveView
            scenarios={scenarios}
            initialScenario={scenarios[0]}
          />
        )}

        {currentTab === "incidents" && <IncidentsView />}

        {currentTab === "evaluation" && <EvaluationView />}

        {currentTab === "security" && <SecurityView />}

        {currentTab === "shop" && (
          <ShopView onSwitchToLive={() => setCurrentTab("live")} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950/80 py-4 text-center text-xs font-mono text-zinc-600">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
          <span>IncidentIQ v2.0 · Autonomous On-Call Control Plane</span>
          <span>LangGraph Multi-Agent Architecture · FastMCP Tools</span>
        </div>
      </footer>
    </div>
  );
}
