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
      const res = await submitApproval(
        activeIncidentId,
        "approve",
        approval.approval_token
      );
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
    <div className="space-y-6">
      {/* 1. Scenario Selector */}
      <ScenarioPicker
        scenarios={scenarios}
        selectedScenario={selectedScenario}
        onSelectScenario={setSelectedScenario}
        onLaunch={handleLaunch}
        isLoading={isLaunching}
      />

      {/* 2. Timeline Stepper (Hero during running, collapsible when completed) */}
      {(status !== "idle" || events.length > 0) && (
        <AgentTimeline
          events={events}
          status={status}
          costUsd={costUsd}
          steps={steps}
          latencyMs={latencyMs}
          onSelectEvidence={setSelectedEvidence}
        />
      )}

      {/* 3. State-Driven Main Panel */}
      {status === "idle" && (
        <div className="bg-zinc-900/50 border border-zinc-800/60 rounded-xl p-12 text-center space-y-3">
          <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center mx-auto text-zinc-400">
            ○
          </div>
          <h3 className="text-sm font-semibold text-zinc-200">No Active Incident</h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto">
            Choose a benchmark scenario above and click &quot;Launch Investigation&quot;, or trigger a chaos fault in the Shop Lab.
          </p>
        </div>
      )}

      {/* Awaiting Approval or Completed Report */}
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

      {/* Abstained View */}
      {status === "abstained" && <AbstainedPanel hypothesis={hypothesis} />}

      {/* Failed View */}
      {status === "failed" && (
        <FailedPanel error={error || undefined} onRetry={handleLaunch} />
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
