"use client";

import React from "react";
import { Play } from "lucide-react";
import { Scenario } from "../types/api";

interface ScenarioPickerProps {
  scenarios: Scenario[];
  selectedScenario: Scenario | null;
  onSelectScenario: (sc: Scenario) => void;
  onLaunch: () => void;
  isLoading?: boolean;
}

export function ScenarioPicker({
  scenarios,
  selectedScenario,
  onSelectScenario,
  onLaunch,
  isLoading,
}: ScenarioPickerProps) {
  return (
    <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono text-xs">
        {/* Left: Scenario [ choose a scenario ▾ ] */}
        <div className="flex items-center gap-3 flex-1 max-w-xl">
          <span className="text-zinc-500 font-medium">Scenario</span>
          <select
            value={selectedScenario?.id || ""}
            onChange={(e) => {
              const sc = scenarios.find((s) => s.id === e.target.value);
              if (sc) onSelectScenario(sc);
            }}
            className="flex-1 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-900 dark:text-zinc-200 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono transition-colors cursor-pointer"
          >
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.number} · {sc.title}
              </option>
            ))}
          </select>
        </div>

        {/* Right: [ Run investigation ] */}
        <button
          onClick={onLaunch}
          disabled={!selectedScenario || isLoading}
          className="flex items-center justify-center gap-2 px-5 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-zinc-950 shadow-[0_0_12px_rgba(16,185,129,0.3)] transition-all active:scale-98 disabled:opacity-40 cursor-pointer"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{isLoading ? "Running..." : "Run investigation"}</span>
        </button>
      </div>

      {/* Subtle scenario description preview */}
      {selectedScenario && (
        <div className="mt-3 pt-3 border-t border-zinc-100 dark:border-zinc-800/60 flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <div className="flex items-center gap-2 truncate pr-4">
            <span className="uppercase text-zinc-500">Alert:</span>
            <span className="text-zinc-700 dark:text-zinc-300 truncate">{selectedScenario.symptom}</span>
          </div>
          <span className="shrink-0 text-zinc-500">Service: {selectedScenario.service}</span>
        </div>
      )}
    </div>
  );
}
