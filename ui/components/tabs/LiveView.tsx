"use client";

import React, { useState } from "react";
import { ScenarioPicker } from "../ScenarioPicker";
import { AgentTimeline } from "../AgentTimeline";
import { ReportView } from "../ReportView";
import { AbstainedPanel } from "../AbstainedPanel";
import { FailedPanel } from "../FailedPanel";
import { ApprovalModal } from "../ApprovalModal";
import { CitationSheet } from "../CitationSheet";
import { Evidence, FeedbackVerdict, IncidentDetail, Scenario } from "../../types/api";
import { useIncidentStream } from "../../hooks/useIncidentStream";
import { createIncident, submitApproval, submitFeedback } from "../../lib/api";

interface LiveViewProps {
  scenarios: Scenario[];
  initialScenario?: Scenario;
  activeIncidentId?: string | null;
  onActiveIncidentChange?: (id: string | null) => void;
  onIncidentCreated?: () => void;
}

export function LiveView({
  scenarios,
  initialScenario,
  activeIncidentId: controlledIncidentId,
  onActiveIncidentChange,
  onIncidentCreated,
}: LiveViewProps) {
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(
    initialScenario || scenarios[0] || null
  );
  const [uncontrolledIncidentId, setUncontrolledIncidentId] = useState<string | null>(null);
  const [optimisticIncident, setOptimisticIncident] = useState<IncidentDetail | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const activeIncidentId =
    controlledIncidentId !== undefined ? controlledIncidentId : uncontrolledIncidentId;

  const setActiveIncidentId = (id: string | null) => {
    if (controlledIncidentId === undefined) {
      setUncontrolledIncidentId(id);
    }
    onActiveIncidentChange?.(id);
  };

  const {
    incident: streamedIncident,
    events,
    status,
    setStatus,
    refreshIncident,
    evidenceList,
    hypothesis,
    approval,
    costUsd,
    steps,
    latencyMs,
    langfuseTraceUrl,
    error,
  } = useIncidentStream(activeIncidentId, () => {
    setOptimisticIncident(null);
    setActiveIncidentId(null);
  });

  const activeIncident =
    streamedIncident && streamedIncident.incident_id === activeIncidentId
      ? streamedIncident
      : optimisticIncident && optimisticIncident.incident_id === activeIncidentId
        ? optimisticIncident
        : null;

  const matchedScenario =
    activeIncident?.scenario_id
      ? scenarios.find((s) => s.id === activeIncident.scenario_id) || null
      : null;

  const activeScenario = selectedScenario || matchedScenario || initialScenario || scenarios[0] || null;

  const handleLaunch = async () => {
    if (!activeScenario) return;
    setIsLaunching(true);
    setActionError(null);
    try {
      const res = await createIncident({
        service: activeScenario.service,
        symptom: activeScenario.symptom,
        window_start: activeScenario.window_start,
        window_end: activeScenario.window_end,
        scenario_id: activeScenario.id,
      });

      setOptimisticIncident({
        incident_id: res.incident_id,
        scenario_id: activeScenario.id,
        alert: {
          service: activeScenario.service,
          symptom: activeScenario.symptom,
          window_start: activeScenario.window_start,
          window_end: activeScenario.window_end,
        },
        status: "queued",
        created_at: Date.now(),
      });
      setActiveIncidentId(res.incident_id);
      onIncidentCreated?.();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to launch incident");
    } finally {
      setIsLaunching(false);
    }
  };

  const handleConfirmApproval = async () => {
    if (!activeIncidentId || !approval?.approval_id) {
      setActionError("Missing approval_id for authorization request.");
      return;
    }
    setActionError(null);
    try {
      await submitApproval(activeIncidentId, "approve", approval.approval_id);
      setStatus("remediation_executed");
      setIsApprovalModalOpen(false);
      await refreshIncident();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Approval execution failed");
    }
  };

  const handleReject = async () => {
    if (!activeIncidentId || !approval?.approval_id) {
      setActionError("Missing approval_id for rejection request.");
      return;
    }
    setActionError(null);
    try {
      await submitApproval(activeIncidentId, "reject", approval.approval_id);
      setStatus("rejected_by_human");
      await refreshIncident();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Reject execution failed");
    }
  };

  const handleSubmitFeedback = async (
    verdict: FeedbackVerdict,
    correctedCategory?: string
  ) => {
    if (!activeIncidentId) return;
    setActionError(null);
    try {
      await submitFeedback(activeIncidentId, {
        verdict,
        corrected_category: correctedCategory,
      });
      await refreshIncident();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to save feedback");
    }
  };

  return (
    <div className="w-full space-y-6">
      <ScenarioPicker
        scenarios={scenarios}
        selectedScenario={activeScenario}
        onSelectScenario={setSelectedScenario}
        onLaunch={handleLaunch}
        isLoading={isLaunching}
      />

      {actionError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs font-mono text-red-700 dark:text-red-300">
          {actionError}
        </div>
      )}

      {(status !== "idle" || events.length > 0) && (
        <AgentTimeline
          alert={
            activeIncident?.alert ||
            (activeScenario
              ? {
                  service: activeScenario.service,
                  symptom: activeScenario.symptom,
                  window_start: activeScenario.window_start,
                  window_end: activeScenario.window_end,
                }
              : undefined)
          }
          events={events}
          status={status}
          costUsd={costUsd}
          steps={steps}
          latencyMs={latencyMs}
          onSelectEvidence={setSelectedEvidence}
        />
      )}

      {status === "idle" && (
        <div className="w-full rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-16 text-center space-y-2 font-mono shadow-xs">
          <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            No active incident
          </div>
          <div className="text-xs text-zinc-500 max-w-md mx-auto">
            {scenarios.length > 0
              ? "Pick a scenario above and launch an investigation."
              : "No scenarios loaded from the backend API yet."}
          </div>
        </div>
      )}

      {(status === "awaiting_approval" ||
        status === "completed" ||
        status === "remediation_executed" ||
        status === "rejected_by_human") && (
        <ReportView
          incident={
            activeIncident
              ? {
                  ...activeIncident,
                  events,
                  langfuse_trace_url: langfuseTraceUrl || activeIncident.langfuse_trace_url,
                }
              : null
          }
          status={status}
          hypothesis={hypothesis}
          evidenceList={evidenceList}
          onSelectEvidence={setSelectedEvidence}
          onRequestApproval={() => setIsApprovalModalOpen(true)}
          onReject={handleReject}
          onSubmitFeedback={handleSubmitFeedback}
        />
      )}

      {status === "abstained" && (
        <AbstainedPanel
          hypothesis={hypothesis}
          evidenceList={evidenceList}
          events={events}
          feedback={activeIncident?.feedback}
          onSubmitFeedback={handleSubmitFeedback}
        />
      )}

      {(status === "failed" || status === "budget_exceeded") && (
        <FailedPanel
          error={
            error ||
            (status === "budget_exceeded"
              ? "Agent step or cost budget exceeded before completion."
              : undefined)
          }
          partialEvidence={evidenceList}
          onRetry={handleLaunch}
        />
      )}

      <CitationSheet
        evidence={selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
      />

      <ApprovalModal
        isOpen={isApprovalModalOpen}
        approval={approval}
        onConfirm={handleConfirmApproval}
        onCancel={() => setIsApprovalModalOpen(false)}
      />
    </div>
  );
}
