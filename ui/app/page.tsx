"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ThemeProvider, useTheme } from "../context/ThemeContext";
import { AppSidebar, NavTab } from "../components/AppSidebar";
import { TopBar } from "../components/TopBar";
import { LiveView } from "../components/tabs/LiveView";
import { IncidentsView } from "../components/tabs/IncidentsView";
import { EvaluationView } from "../components/tabs/EvaluationView";
import { SecurityView } from "../components/tabs/SecurityView";
import { ShopView } from "../components/tabs/ShopView";
import { Scenario } from "../types/api";
import { fetchIncidents, fetchScenarios } from "../lib/api";

function IncidentIQApp() {
  const { theme } = useTheme();
  const [currentTab, setCurrentTab] = useState<NavTab>("live");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [incidentCount, setIncidentCount] = useState<number>(0);

  const refreshIncidentCount = () => {
    fetchIncidents()
      .then((data) => setIncidentCount(data.length))
      .catch(() => {});
  };

  useEffect(() => {
    fetchScenarios()
      .then((data) => setScenarios(data))
      .catch((err) => console.error("Error loading scenarios:", err));
    fetchIncidents()
      .then((data) => setIncidentCount(data.length))
      .catch(() => {});
  }, []);

  return (
    <div
      className={`min-h-screen w-full ${
        theme === "dark" ? "dark bg-[#09090b] text-[#f4f4f5]" : "bg-[#fafafa] text-[#18181b]"
      } flex transition-colors duration-150`}
    >
      {/* Collapsible Left Sidebar */}
      <AppSidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        incidentCount={incidentCount}
      />

      {/* Full-width Main Area */}
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

        {/* Full-Screen Animated Content Workspace */}
        <main className="flex-1 w-full px-6 py-6 md:px-10 md:py-8 overflow-x-hidden">
          <h1 className="sr-only">
            IncidentIQ — Autonomous AI On-Call Triage & Root Cause Control Plane
          </h1>
          <AnimatePresence mode="wait">
            <motion.div
              key={currentTab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="w-full"
            >
              {currentTab === "live" && (
                <LiveView
                  scenarios={scenarios}
                  initialScenario={scenarios[0]}
                  onIncidentCreated={refreshIncidentCount}
                />
              )}

              {currentTab === "incidents" && <IncidentsView />}

              {currentTab === "evaluation" && <EvaluationView />}

              {currentTab === "security" && <SecurityView />}

              {currentTab === "shop" && (
                <ShopView onSwitchToLive={() => setCurrentTab("live")} />
              )}
            </motion.div>
          </AnimatePresence>
        </main>
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
