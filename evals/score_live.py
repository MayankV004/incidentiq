"""Evaluates real/shadow-mode incidents scored via human feedback in SQLite."""

import argparse
import json
import os
import statistics
from datetime import UTC, datetime
from typing import Any

from incidentiq.db.repository import list_labeled_incidents_for_scoring


def compute_live_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Computes empirical accuracy, abstention precision, calibration, latency, and cost."""
    total = len(records)
    if total == 0:
        return {
            "run_name": "live-feedback",
            "timestamp": datetime.now(UTC).isoformat(),
            "labeled_incidents": 0,
            "accuracy_pct": None,
            "abstention_precision_pct": None,
            "mean_confidence": None,
            "calibration_gap": None,
            "mean_cost_usd": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "verdicts": {},
            "notes": "No labeled incidents with human feedback found in database.",
        }

    verdict_counts: dict[str, int] = {
        "correct_root_cause": 0,
        "wrong_root_cause": 0,
        "good_abstention": 0,
        "false_alarm": 0,
    }
    confidences: list[float] = []
    outcomes: list[float] = []
    costs: list[float] = []
    latencies: list[float] = []

    for rec in records:
        fb = rec.get("feedback") or {}
        verdict = str(fb.get("verdict") or "")
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        is_correct = verdict in ("correct_root_cause", "good_abstention")
        outcomes.append(1.0 if is_correct else 0.0)

        hyp = rec.get("hypothesis") or {}
        if isinstance(hyp, dict) and hyp.get("confidence") is not None:
            confidences.append(float(hyp["confidence"]))
        costs.append(float(rec.get("cost_usd") or 0.0))
        latencies.append(float(rec.get("latency_ms") or 0.0))

    accuracy_pct = round(statistics.mean(outcomes) * 100.0, 1)
    abstain_total = verdict_counts["good_abstention"] + verdict_counts["false_alarm"]
    abstention_pct = (
        round((verdict_counts["good_abstention"] / abstain_total) * 100.0, 1)
        if abstain_total > 0
        else None
    )
    mean_conf = round(statistics.mean(confidences), 3) if confidences else None
    calibration_gap = (
        round(abs(mean_conf - (accuracy_pct / 100.0)), 3)
        if mean_conf is not None
        else None
    )
    sorted_lat = sorted(latencies)
    p50_lat = round(statistics.median(sorted_lat), 1)
    p95_lat = round(sorted_lat[min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)], 1)

    return {
        "run_name": "live-feedback",
        "timestamp": datetime.now(UTC).isoformat(),
        "labeled_incidents": total,
        "accuracy_pct": accuracy_pct,
        "abstention_precision_pct": abstention_pct,
        "mean_confidence": mean_conf,
        "calibration_gap": calibration_gap,
        "mean_cost_usd": round(statistics.mean(costs), 6),
        "latency_p50_ms": p50_lat,
        "latency_p95_ms": p95_lat,
        "verdicts": verdict_counts,
        "notes": "measured from real SQLite incidents labeled via /v1/incidents/{id}/feedback",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score labeled live/shadow incidents")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    records = list_labeled_incidents_for_scoring()
    summary = compute_live_metrics(records)

    acc_str = f"{summary['accuracy_pct']}%" if summary["accuracy_pct"] is not None else "—"
    abs_str = (
        f"{summary['abstention_precision_pct']}%"
        if summary["abstention_precision_pct"] is not None
        else "—"
    )
    cost_str = f"${summary['mean_cost_usd']}" if summary["mean_cost_usd"] is not None else "—"
    lat_str = (
        f"{summary['latency_p50_ms']}ms / {summary['latency_p95_ms']}ms"
        if summary["latency_p50_ms"] is not None
        else "— / —"
    )

    print("\n=======================================================")
    print("LIVE / SHADOW-MODE EVALUATION REPORT")
    print("=======================================================")
    print(f"Labeled Incidents    : {summary['labeled_incidents']}")
    print(f"Empirical Accuracy   : {acc_str}")
    print(f"Abstention Precision : {abs_str}")
    print(f"Mean Confidence      : {summary['mean_confidence']} (Calibration gap: {summary['calibration_gap']})")
    print(f"Mean Cost / Incident : {cost_str}")
    print(f"Latency p50 / p95    : {lat_str}")
    print(f"Verdicts             : {summary['verdicts']}")
    print("=======================================================\n")

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"[+] Wrote live evaluation report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
