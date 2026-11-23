"use client";

import React, { useEffect, useState } from "react";
import { ThemeProvider } from "../context/ThemeContext";
import { AppSidebar, NavTab } from "../components/AppSidebar";
import { TopBar } from "../components/TopBar";
import { LiveView } from "../components/tabs/LiveView";
import { IncidentsView } from "../components/tabs/IncidentsView";
import { EvaluationView } from "../components/tabs/EvaluationView";
import { SecurityView } from "../components/tabs/SecurityView";
import { ShopView } from "../components/tabs/ShopView";
import { Scenario } from "../types/api";
import { fetchScenarios } from "../lib/api";

function IncidentIQApp() {
  const [currentTab, setCurrentTab] = useState<NavTab>("live");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  useEffect(() => {
    fetchScenarios()
      .then((data) => setScenarios(data))
      .catch((err) => console.error("Error loading scenarios:", err));
  }, []);

  return (
    <div className="min-h-screen bg-[#fafafa] dark:bg-[#09090b] text-zinc-900 dark:text-zinc-100 flex transition-colors duration-200">
      {/* Collapsible Left Sidebar */}
      <AppSidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        incidentCount={8}
      />

      {/* Main Content Area */}
      <div
        className={`flex-1 flex flex-col min-h-screen transition-all duration-200 ${
          isSidebarCollapsed ? "ml-16" : "ml-64"
        }`}
      >
        {/* Top Notion/Linear Breadcrumb Bar */}
        <TopBar
          currentTab={currentTab}
          isSidebarCollapsed={isSidebarCollapsed}
          onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />

        {/* Tab Content */}
        <main className="flex-1 p-6 md:p-8">
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

        {/* Minimalist Notion Footer */}
        <footer className="border-t border-zinc-200/70 dark:border-zinc-900/80 px-8 py-3.5 text-xs font-mono text-zinc-400 dark:text-zinc-600 flex items-center justify-between">
          <span>IncidentIQ · Autonomous Multi-Agent On-Call Control Plane</span>
          <span>FastMCP · LangGraph Engine</span>
        </footer>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <ThemeProvider>
      <IncidentIQApp />
    </ThemeProvider>
  );
}
