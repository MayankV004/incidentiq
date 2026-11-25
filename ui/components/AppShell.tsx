"use client";

import React, { Suspense, createContext, useCallback, useContext, useEffect, useState } from "react";
import { useTheme } from "../context/ThemeContext";
import { AppSidebar } from "./AppSidebar";
import { TopBar } from "./TopBar";
import { fetchIncidents } from "../lib/api";

interface AppShellContextValue {
  incidentCount: number;
  refreshIncidentCount: () => void;
  isInvestigating: boolean;
  setIsInvestigating: (val: boolean) => void;
  activeIncidentTitle?: string;
  setActiveIncidentTitle: (title?: string) => void;
}

const AppShellContext = createContext<AppShellContextValue>({
  incidentCount: 0,
  refreshIncidentCount: () => {},
  isInvestigating: false,
  setIsInvestigating: () => {},
  activeIncidentTitle: undefined,
  setActiveIncidentTitle: () => {},
});

export function useAppShell() {
  return useContext(AppShellContext);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [incidentCount, setIncidentCount] = useState<number>(0);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [activeIncidentTitle, setActiveIncidentTitle] = useState<string | undefined>(undefined);

  const refreshIncidentCount = useCallback(() => {
    fetchIncidents()
      .then((data) => setIncidentCount(data.length))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchIncidents()
      .then((data) => setIncidentCount(data.length))
      .catch(() => {});
  }, []);

  return (
    <AppShellContext.Provider
      value={{
        incidentCount,
        refreshIncidentCount,
        isInvestigating,
        setIsInvestigating,
        activeIncidentTitle,
        setActiveIncidentTitle,
      }}
    >
      <div
        className={`min-h-screen w-full ${
          theme === "dark" ? "dark bg-[#09090b] text-[#f4f4f5]" : "bg-[#fafafa] text-[#18181b]"
        } flex transition-colors duration-150`}
      >
        <Suspense fallback={null}>
          <AppSidebar
            isCollapsed={isSidebarCollapsed}
            onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
            isInvestigating={isInvestigating}
            incidentCount={incidentCount}
          />
        </Suspense>

        <div
          className={`flex-1 flex flex-col min-h-screen transition-all duration-200 ${
            isSidebarCollapsed ? "ml-16" : "ml-64"
          }`}
        >
          <Suspense fallback={null}>
            <TopBar
              isSidebarCollapsed={isSidebarCollapsed}
              onToggleSidebar={() => setIsSidebarCollapsed((prev) => !prev)}
              activeIncidentTitle={activeIncidentTitle}
              isInvestigating={isInvestigating}
            />
          </Suspense>

          <main className="flex-1 w-full px-6 py-6 md:px-10 md:py-8 overflow-x-hidden">
            <h1 className="sr-only">
              IncidentIQ — Autonomous AI On-Call Triage & Root Cause Control Plane
            </h1>
            {children}
          </main>
        </div>
      </div>
    </AppShellContext.Provider>
  );
}
