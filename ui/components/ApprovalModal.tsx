"use client";

import React, { useState } from "react";
import { ShieldAlert, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { ApprovalInfo } from "../types/api";

interface ApprovalModalProps {
  isOpen: boolean;
  approval: ApprovalInfo | null;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
}

export function ApprovalModal({
  isOpen,
  approval,
  onConfirm,
  onCancel,
}: ApprovalModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !approval) return null;

  const action = approval.action;

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-zinc-100">
              Authorize Remediation Action
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Human-in-the-loop authorization gate required before executing
            </p>
          </div>
        </div>

        {/* Action Details */}
        <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-400">Action Type</span>
            <span className="font-mono text-zinc-200 font-semibold uppercase">
              {action?.type || "review_config"}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-400">Target Service</span>
            <span className="font-mono text-zinc-200">{action?.target || "orders"}</span>
          </div>

          {action?.parameters && Object.keys(action.parameters).length > 0 && (
            <div className="pt-2 border-t border-zinc-800 text-xs">
              <span className="text-zinc-400 block mb-1">Parameters</span>
              <pre className="text-[11px] font-mono text-zinc-300 bg-zinc-900 p-2 rounded border border-zinc-800">
                {JSON.stringify(action.parameters, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Security / Dry-Run Guarantee */}
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400 mt-0.5" />
          <div>
            <span className="font-semibold text-emerald-200">
              Safe Dry-Run Guarantee:
            </span>{" "}
            Remediation tool runs in strictly sandboxed dry-run mode. Verification receipts are generated without mutating production state.
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-zinc-100 text-zinc-950 hover:bg-white active:scale-98 transition-all disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Executing Dry-Run...</span>
              </>
            ) : (
              <span>Confirm & Execute (Dry-Run)</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
