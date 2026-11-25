"use client";

import React, { useEffect, useState } from "react";
import { LiveView } from "../components/tabs/LiveView";
import { useAppShell } from "../components/AppShell";
import { Scenario } from "../types/api";
import { fetchScenarios } from "../lib/api";

export default function LiveTriagePage() {
  const { refreshIncidentCount } = useAppShell();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null);

  const selectActiveIncident = (id: string | null) => {
    setActiveIncidentId(id);
    if (typeof window === "undefined") return;
    try {
      if (id) {
        window.sessionStorage.setItem("incidentiq.activeIncidentId", id);
        const url = new URL(window.location.href);
        url.searchParams.set("incident", id);
        window.history.replaceState({}, "", url.toString());
      } else {
        window.sessionStorage.removeItem("incidentiq.activeIncidentId");
        const url = new URL(window.location.href);
        url.searchParams.delete("incident");
        window.history.replaceState({}, "", url.toString());
      }
    } catch {
      // ignore storage errors
    }
  };

  useEffect(() => {
    fetchScenarios()
      .then((data) => {
        setScenarios(data);
        if (typeof window !== "undefined") {
          const urlId = new URLSearchParams(window.location.search).get("incident");
          const savedId = window.sessionStorage.getItem("incidentiq.activeIncidentId");
          const targetId = urlId || savedId;
          if (targetId) {
            setActiveIncidentId(targetId);
          }
        }
      })
      .catch((err) => console.error("Error loading scenarios:", err));
  }, []);

  return (
    <LiveView
      scenarios={scenarios}
      initialScenario={scenarios[0]}
      activeIncidentId={activeIncidentId}
      onActiveIncidentChange={selectActiveIncident}
      onIncidentCreated={refreshIncidentCount}
    />
  );
}
