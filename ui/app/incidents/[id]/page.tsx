"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { LiveView } from "../../../components/tabs/LiveView";
import { useAppShell } from "../../../components/AppShell";
import { fetchScenarios } from "../../../lib/api";
import { Scenario } from "../../../types/api";

function IncidentDetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { refreshIncidentCount } = useAppShell();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  const incidentId = params?.id ? decodeURIComponent(params.id) : null;

  useEffect(() => {
    fetchScenarios()
      .then((data) => setScenarios(data))
      .catch((err) => console.error("Error loading scenarios:", err));
  }, []);

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between">
        <Link
          href="/incidents"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Incidents History</span>
        </Link>
      </div>

      <LiveView
        scenarios={scenarios}
        initialScenario={scenarios[0]}
        activeIncidentId={incidentId}
        onActiveIncidentChange={(newId) => {
          if (newId) {
            router.push(`/incidents/${encodeURIComponent(newId)}`);
          } else {
            router.push("/incidents");
          }
        }}
        onIncidentCreated={refreshIncidentCount}
      />
    </div>
  );
}

export default function IncidentDetailPage() {
  return (
    <Suspense fallback={<div className="w-full p-8 text-xs font-mono text-zinc-500">Loading incident...</div>}>
      <IncidentDetailContent />
    </Suspense>
  );
}
