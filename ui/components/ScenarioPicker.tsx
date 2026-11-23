"use client";

import React from "react";
import { Play, Sparkles, ChevronRight } from "lucide-react";
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
    <div className="bg-zinc-900 border border-zinc-800/80 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-zinc-300" />
            <h3 className="text-xs font-semibold text-zinc-100 uppercase tracking-wider">
              On-Call Evaluation Scenario
            </h3>
          </div>
          <p className="text-xs text-zinc-400">
            Select a benchmark scenario from the evaluation suite or inject live chaos
          </p>
        </div>

        {/* Launch Button */}
        <button
          onClick={onLaunch}
          disabled={!selectedScenario || isLoading}
          className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold bg-zinc-100 text-zinc-950 hover:bg-white active:scale-98 transition-all disabled:opacity-40 cursor-pointer shadow-sm"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{isLoading ? "Dispatching..." : "Launch Investigation"}</span>
        </button>
      </div>

      {/* Select Dropdown & Scenario Preview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-zinc-800/60">
        <div className="md:col-span-1">
          <label className="text-[11px] font-medium text-zinc-400 block mb-1">
            Benchmark Scenario
          </label>
          <select
            value={selectedScenario?.id || ""}
            onChange={(e) => {
              const sc = scenarios.find((s) => s.id === e.target.value);
              if (sc) onSelectScenario(sc);
            }}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-zinc-600 font-mono"
          >
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.number} · {sc.title}
              </option>
            ))}
          </select>
        </div>

        {/* Selected Scenario Metadata */}
        <div className="md:col-span-2 bg-zinc-950/80 p-3 rounded-lg border border-zinc-800/60 flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-mono text-zinc-400 uppercase text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800">
                Service: {selectedScenario?.service || "orders"}
              </span>
              <span className="text-zinc-600">·</span>
              <span className="text-zinc-300 font-medium truncate">
                {selectedScenario?.symptom || "Select a scenario to inspect alert"}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 pt-2 border-t border-zinc-900">
            <span>Ground Truth: {selectedScenario?.expected_root_cause || "—"}</span>
            <span>Target Action: {selectedScenario?.expected_action || "—"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
