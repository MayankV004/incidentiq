"use client";

import React from "react";
import { ChevronRight, PanelLeft, Sun, Moon, Activity } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { NavTab } from "./AppSidebar";

interface TopBarProps {
  currentTab: NavTab;
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  activeIncidentTitle?: string;
  isInvestigating?: boolean;
}

export function TopBar({
  currentTab,
  isSidebarCollapsed,
  onToggleSidebar,
  activeIncidentTitle,
  isInvestigating,
}: TopBarProps) {
  const { theme, toggleTheme } = useTheme();

  const tabLabels: Record<NavTab, string> = {
    live: "Live Triage",
    incidents: "Incidents History",
    evaluation: "Evaluation Suite",
    security: "Security Matrix",
    shop: "Shop Chaos Lab",
  };

  return (
    <header className="sticky top-0 z-30 h-14 bg-white/80 dark:bg-[#09090b]/80 backdrop-blur-md border-b border-zinc-200/80 dark:border-zinc-800/80 px-6 flex items-center justify-between transition-colors">
      {/* Left: Breadcrumbs & Sidebar Toggle */}
      <div className="flex items-center gap-3">
        {isSidebarCollapsed && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 -ml-2 rounded-md text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800/60 transition-colors"
            title="Expand sidebar"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        )}

        <div className="flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500 font-medium">
          <span className="hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">IncidentIQ</span>
          <ChevronRight className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600" />
          <span className="text-zinc-900 dark:text-zinc-200 font-semibold">
            {tabLabels[currentTab]}
          </span>
          {activeIncidentTitle && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600" />
              <span className="text-zinc-500 dark:text-zinc-400 font-mono truncate max-w-[200px]">
                {activeIncidentTitle}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Right: Status Pill & Actions */}
      <div className="flex items-center gap-3">
        {isInvestigating ? (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-600 dark:text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span>Autonomous Triage Active</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-400 dark:text-zinc-500">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]" />
            <span>Ready</span>
          </div>
        )}

        {/* Quick theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          title="Toggle theme"
        >
          {theme === "dark" ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-zinc-600" />
          )}
        </button>
      </div>
    </header>
  );
}
