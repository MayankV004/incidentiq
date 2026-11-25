"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { IncidentsView } from "../../components/tabs/IncidentsView";

export default function IncidentsPage() {
  const router = useRouter();

  return (
    <IncidentsView
      onSelectIncident={(id) => {
        if (typeof window !== "undefined") {
          try {
            window.sessionStorage.setItem("incidentiq.activeIncidentId", id);
          } catch {
            // ignore storage errors
          }
        }
        router.push(`/incidents/${encodeURIComponent(id)}`);
      }}
    />
  );
}
