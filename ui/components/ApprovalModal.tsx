"use client";

import React, { useState } from "react";
import { ShieldAlert, CheckCircle2, Loader2 } from "lucide-react";
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
      <div className="w-full max-w-md bg-white dark:bg-[#121215] border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500 border border-amber-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Authorize Remediation Action
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              Human-in-the-loop authorization gate required before executing
            </p>
          </div>
        </div>

        {/* Action Details */}
        <div className="bg-zinc-50 dark:bg-zinc-950 p-4 rounded-lg border border-zinc-200 dark:border-zinc-800/80 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">Action Type</span>
            <span className="text-zinc-900 dark:text-zinc-100 font-semibold uppercase">
              {action?.type || "review_config"}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-zinc-500">Target Service</span>
            <span className="text-zinc-900 dark:text-zinc-100">{action?.target || "orders"}</span>
          </div>

          {action?.parameters && Object.keys(action.parameters).length > 0 && (
            <div className="pt-2 border-t border-zinc-200 dark:border-zinc-800">
              <span className="text-zinc-500 block mb-1">Parameters</span>
              <pre className="text-[11px] text-zinc-800 dark:text-zinc-300 bg-white dark:bg-zinc-900 p-2 rounded border border-zinc-200 dark:border-zinc-800">
                {JSON.stringify(action.parameters, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Security / Dry-Run Guarantee */}
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-800 dark:text-emerald-300">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" />
          <div>
            <span className="font-semibold text-emerald-900 dark:text-emerald-200">
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
            className="px-4 py-2 rounded-lg text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50 cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-zinc-950 shadow-[0_0_12px_rgba(16,185,129,0.3)] transition-all active:scale-98 disabled:opacity-50 cursor-pointer"
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
