"use client";

import React from "react";
import {
  Radio,
  Activity,
  BarChart3,
  ShieldCheck,
  Server,
  PanelLeftClose,
  PanelLeft,
  Sun,
  Moon,
  Zap,
} from "lucide-react";
import { useTheme } from "../context/ThemeContext";

export type NavTab = "live" | "incidents" | "evaluation" | "security" | "shop";

interface AppSidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isInvestigating?: boolean;
  incidentCount?: number;
}

export function AppSidebar({
  currentTab,
  onSelectTab,
  isCollapsed,
  onToggleCollapse,
  isInvestigating,
  incidentCount = 8,
}: AppSidebarProps) {
  const { theme, toggleTheme } = useTheme();

  const navItems: {
    id: NavTab;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string | number;
  }[] = [
    { id: "live", label: "Live Triage", icon: Radio, badge: isInvestigating ? "LIVE" : undefined },
    { id: "incidents", label: "Incidents History", icon: Activity, badge: incidentCount },
    { id: "evaluation", label: "Evaluation Suite", icon: BarChart3 },
    { id: "security", label: "Security Matrix", icon: ShieldCheck, badge: "100%" },
    { id: "shop", label: "Shop Chaos Lab", icon: Server },
  ];

  return (
    <aside
      className={`fixed top-0 left-0 h-screen z-40 flex flex-col border-r transition-all duration-200 select-none ${
        isCollapsed ? "w-16" : "w-64"
      } bg-white dark:bg-[#0c0c0e] border-zinc-200 dark:border-zinc-800/80`}
    >
      {/* Workspace Brand / Header */}
      <div className="h-14 px-3 flex items-center justify-between border-b border-zinc-200/70 dark:border-zinc-800/60">
        {!isCollapsed && (
          <div className="flex items-center gap-2.5 overflow-hidden pl-1">
            <div className="w-6 h-6 rounded-md bg-zinc-900 dark:bg-emerald-500/10 dark:border dark:border-emerald-500/30 flex items-center justify-center text-white dark:text-emerald-400 font-bold text-xs tracking-tighter shrink-0 shadow-xs">
              <Zap className="w-3.5 h-3.5 fill-current" />
            </div>
            <div className="flex flex-col overflow-hidden">
              <span className="font-semibold text-xs tracking-tight text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                IncidentIQ
                <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium">
                  v2.0
                </span>
              </span>
              <span className="text-[10px] text-zinc-400 truncate font-mono">
                Production On-Call
              </span>
            </div>
          </div>
        )}

        {isCollapsed && (
          <div className="mx-auto">
            <div className="w-7 h-7 rounded-md bg-zinc-900 dark:bg-emerald-500/10 dark:border dark:border-emerald-500/30 flex items-center justify-center text-white dark:text-emerald-400 font-bold text-xs">
              <Zap className="w-4 h-4 fill-current" />
            </div>
          </div>
        )}

        {/* Collapse toggle */}
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/60 transition-colors"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <PanelLeft className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-all group ${
                isActive
                  ? "bg-zinc-100 dark:bg-zinc-800/80 text-zinc-900 dark:text-zinc-100 shadow-xs dark:shadow-none font-semibold"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100/60 dark:hover:bg-zinc-900/60"
              } ${isCollapsed ? "justify-center px-0" : ""}`}
              title={isCollapsed ? item.label : undefined}
            >
              <div className="relative shrink-0">
                <Icon
                  className={`w-4 h-4 ${
                    isActive
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300"
                  }`}
                />
                {item.id === "live" && isInvestigating && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                )}
              </div>

              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between text-left truncate">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                        isActive
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold"
                          : "bg-zinc-200/60 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer / System Health & Theme Toggle */}
      <div className="p-3 border-t border-zinc-200/70 dark:border-zinc-800/60 space-y-2">
        {/* System Health */}
        {!isCollapsed && (
          <div className="px-2 py-1.5 rounded-lg bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200/60 dark:border-zinc-800/40 flex items-center justify-between text-[11px] font-mono text-zinc-500 dark:text-zinc-400">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]" />
              <span>Control Plane</span>
            </div>
            <span className="text-[10px] text-zinc-400">:8000</span>
          </div>
        )}

        {/* Theme Switcher Button */}
        <button
          onClick={toggleTheme}
          className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800/60 transition-colors ${
            isCollapsed ? "justify-center px-0" : ""
          }`}
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          {theme === "dark" ? (
            <Sun className="w-4 h-4 text-amber-400 shrink-0" />
          ) : (
            <Moon className="w-4 h-4 text-zinc-600 shrink-0" />
          )}
          {!isCollapsed && (
            <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
          )}
        </button>
      </div>
    </aside>
  );
}
