"use client";

import React, { useState } from "react";
import { ScenarioPicker } from "../ScenarioPicker";
import { AgentTimeline } from "../AgentTimeline";
import { ReportView } from "../ReportView";
import { AbstainedPanel } from "../AbstainedPanel";
import { FailedPanel } from "../FailedPanel";
import { ApprovalModal } from "../ApprovalModal";
import { CitationSheet } from "../CitationSheet";
import { Evidence, IncidentDetail, Scenario } from "../../types/api";
import { useIncidentStream } from "../../hooks/useIncidentStream";
import { createIncident, submitApproval } from "../../lib/api";

interface LiveViewProps {
  scenarios: Scenario[];
  initialScenario?: Scenario;
}

export function LiveView({ scenarios, initialScenario }: LiveViewProps) {
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(
    initialScenario || scenarios[0] || null
  );
  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null);
  const [activeIncident, setActiveIncident] = useState<IncidentDetail | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);

  // Connect SSE streaming hook
  const {
    events,
    status,
    setStatus,
    evidenceList,
    hypothesis,
    approval,
    costUsd,
    steps,
    latencyMs,
    error,
  } = useIncidentStream(activeIncidentId);

  const handleLaunch = async () => {
    if (!selectedScenario) return;
    setIsLaunching(true);
    try {
      const res = await createIncident({
        service: selectedScenario.service,
        symptom: selectedScenario.symptom,
        window_start: selectedScenario.window_start,
        window_end: selectedScenario.window_end,
        scenario_id: selectedScenario.id,
      });

      setActiveIncidentId(res.incident_id);
      setActiveIncident({
        incident_id: res.incident_id,
        scenario_id: selectedScenario.id,
        alert: {
          service: selectedScenario.service,
          symptom: selectedScenario.symptom,
          window_start: selectedScenario.window_start,
          window_end: selectedScenario.window_end,
        },
        status: "queued",
        created_at: Date.now(),
      });
    } catch (err) {
      console.error("Failed to launch incident:", err);
    } finally {
      setIsLaunching(false);
    }
  };

  const handleConfirmApproval = async () => {
    if (!activeIncidentId || !approval?.approval_token) return;
    try {
      await submitApproval(activeIncidentId, "approve", approval.approval_token);
      setStatus("remediation_executed");
      setIsApprovalModalOpen(false);
    } catch (err) {
      console.error("Approval execution failed:", err);
    }
  };

  const handleReject = async () => {
    if (!activeIncidentId || !approval?.approval_token) return;
    try {
      await submitApproval(activeIncidentId, "reject", approval.approval_token);
      setStatus("rejected_by_human");
    } catch (err) {
      console.error("Reject execution failed:", err);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 1. Scenario Selector */}
      <ScenarioPicker
        scenarios={scenarios}
        selectedScenario={selectedScenario}
        onSelectScenario={setSelectedScenario}
        onLaunch={handleLaunch}
        isLoading={isLaunching}
      />

      {/* 2. Timeline Stepper (Full-width hero while running, collapses to 1-line header when done) */}
      {(status !== "idle" || events.length > 0) && (
        <AgentTimeline
          alert={activeIncident?.alert || (selectedScenario ? {
            service: selectedScenario.service,
            symptom: selectedScenario.symptom,
            window_start: selectedScenario.window_start,
            window_end: selectedScenario.window_end,
          } : undefined)}
          events={events}
          status={status}
          costUsd={costUsd}
          steps={steps}
          latencyMs={latencyMs}
          onSelectEvidence={setSelectedEvidence}
        />
      )}

      {/* 3. Wireframe Empty State for Idle */}
      {status === "idle" && (
        <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-14 text-center space-y-2 font-mono shadow-xs">
          <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            No active incident
          </div>
          <div className="text-xs text-zinc-500 max-w-md mx-auto">
            Pick a scenario, or inject a fault in Shop Control.
          </div>
        </div>
      )}

      {/* 4. Awaiting Approval or Completed Report */}
      {(status === "awaiting_approval" ||
        status === "completed" ||
        status === "remediation_executed" ||
        status === "rejected_by_human") && (
        <ReportView
          incident={activeIncident}
          status={status}
          hypothesis={hypothesis}
          evidenceList={evidenceList}
          onSelectEvidence={setSelectedEvidence}
          onRequestApproval={() => setIsApprovalModalOpen(true)}
          onReject={handleReject}
        />
      )}

      {/* 5. Abstained State Panel */}
      {status === "abstained" && <AbstainedPanel hypothesis={hypothesis} />}

      {/* 6. Failed State Panel */}
      {status === "failed" && (
        <FailedPanel
          error={error || undefined}
          partialEvidence={evidenceList}
          onRetry={handleLaunch}
        />
      )}

      {/* Slide-over Citation Drawer */}
      <CitationSheet
        evidence={selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
      />

      {/* Approval Confirmation Dialog */}
      <ApprovalModal
        isOpen={isApprovalModalOpen}
        approval={approval}
        onConfirm={handleConfirmApproval}
        onCancel={() => setIsApprovalModalOpen(false)}
      />
    </div>
  );
}
