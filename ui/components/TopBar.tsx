"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, PanelLeft, Sun, Moon } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

interface TopBarProps {
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  activeIncidentTitle?: string;
  isInvestigating?: boolean;
}

export function TopBar({
  isSidebarCollapsed,
  onToggleSidebar,
  activeIncidentTitle,
  isInvestigating,
}: TopBarProps) {
  const { theme, toggleTheme } = useTheme();
  const pathname = usePathname() || "/";

  const routeInfo = (() => {
    if (pathname.startsWith("/incidents/")) {
      const incidentId = decodeURIComponent(pathname.slice("/incidents/".length));
      return { label: "Incidents History", href: "/incidents", subLabel: incidentId };
    }
    if (pathname === "/incidents") return { label: "Incidents History", href: "/incidents" };
    if (pathname === "/evaluation") return { label: "Evaluation Suite", href: "/evaluation" };
    if (pathname === "/security") return { label: "Security Matrix", href: "/security" };
    if (pathname === "/shop") return { label: "Shop Chaos Lab", href: "/shop" };
    return { label: "Live Triage", href: "/" };
  })();

  const breadcrumbTail = routeInfo.subLabel || activeIncidentTitle;

  return (
    <header className="sticky top-0 z-30 h-14 bg-white/90 dark:bg-[#09090b]/90 backdrop-blur-md border-b border-zinc-200/80 dark:border-zinc-800/80 px-6 flex items-center justify-between transition-colors">
      {/* Left: Breadcrumbs & Single Expand Button when collapsed */}
      <div className="flex items-center gap-3">
        {isSidebarCollapsed && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 -ml-2 rounded-md text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800/60 transition-colors cursor-pointer"
            title="Expand sidebar"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        )}

        <div className="flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500 font-medium">
          <Link href="/" className="hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">
            IncidentIQ
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600" />
          <Link
            href={routeInfo.href}
            className="text-zinc-900 dark:text-zinc-200 font-semibold hover:underline"
          >
            {routeInfo.label}
          </Link>
          {breadcrumbTail && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600" />
              <span className="text-zinc-500 dark:text-zinc-400 font-mono truncate max-w-[200px]">
                {breadcrumbTail}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Right: Status Pill & Actions */}
      <div className="flex items-center gap-3">
        {isInvestigating ? (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-lime-400/10 border border-lime-400/30 text-xs font-mono text-lime-600 dark:text-lime-400">
            <span className="w-2 h-2 rounded-full bg-lime-400 animate-ping shadow-[0_0_6px_#a3e635]" />
            <span>Autonomous Triage Active</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-400 dark:text-zinc-500">
            <span className="w-1.5 h-1.5 rounded-full bg-lime-400 shadow-[0_0_8px_#a3e635]" />
            <span>Ready</span>
          </div>
        )}

        {/* Quick theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
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
