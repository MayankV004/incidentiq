"""Generates README benchmark and retrieval sections directly from committed result JSONs."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
RESULTS_DIR = ROOT / "evals" / "results"


def _load(name: str) -> dict[str, Any]:
    with open(RESULTS_DIR / name) as f:
        return json.load(f)


def build_retrieval_block(ret: dict[str, Any]) -> str:
    return (
        "<!-- BEGIN_RETRIEVAL_STATS -->\n"
        "* **Verified Benchmark Performance (`evals/run_retrieval_eval.py`, `evals/results/retrieval_summary.json`):**\n"
        f"  * **Hit@3:** `{ret['hit_at_3_pct']:.1f}%` ({ret['hit_at_3_count']}/{ret['total_queries']} target runbooks/postmortems retrieved in top 3).\n"
        f"  * **MRR (Mean Reciprocal Rank):** `{ret['mrr']:.4f}` across the {ret['total_queries']}-query SRE test suite.\n"
        "<!-- END_RETRIEVAL_STATS -->"
    )


def build_eval_block(
    v2_sim: dict[str, Any],
    v2_live: dict[str, Any],
    redteam: dict[str, Any],
) -> str:
    live_by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in v2_live.get("detailed_results", []):
        live_by_scenario.setdefault(row["scenario_id"], []).append(row)

    sim_by_scenario = {
        row["scenario_id"]: row for row in v2_sim.get("detailed_results", [])
    }

    lines = [
        "<!-- BEGIN_EVAL_TABLES -->",
        "### A. High-Level Performance Comparison",
        "",
        "> **Measurement Disclosure:** Offline `v2-optimized` figures come from `DATA_MODE=replay` with deterministic rule-engine fallback (`simulated`). Live `v2-live` figures were measured against Groq (`groq/openai/gpt-oss-120b`) over 3 repeats (`24` runs) using replay scenario telemetry. Note: pre-optimization `v1-baseline.json` was overwritten in commit `e6a092e` (original baseline `62.5%` simulated exists only in git commit `7baa7d5`); therefore only verified current artifacts are tabulated below.",
        "",
        "| Evaluation Dimension | `v2-optimized` (offline replay, simulated) | `v2-live` (Groq `gpt-oss-120b`, measured, 3x8=24 runs) | Target / SLA |",
        "|---|---|---|---|",
        f"| **Root-Cause Diagnostic Accuracy** | {v2_sim['accuracy_pct']:.1f}% (simulated) | **{v2_live['accuracy_pct']:.1f}% (±{v2_live['accuracy_std_pct']:.1f}%)** | ≥ 80.0% |",
        f"| **Claim Groundedness Gate** | {v2_sim['groundedness_pct']:.1f}% (simulated) | **{v2_live['groundedness_pct']:.1f}%** | ≥ 90.0% |",
        f"| **Calibrated Honest Abstention** | {v2_sim['abstention_correct_pct']:.1f}% (simulated) | **{v2_live['abstention_correct_pct']:.1f}%** | ≥ 75.0% |",
        f"| **Action Safety (Zero Unapproved Actions)** | {v2_sim['action_safety_pct']:.1f}% | **{v2_live['action_safety_pct']:.1f}%** | 100.0% |",
        f"| **Adversarial Red-Team Defense** (`evals/redteam/run_redteam.py`) | — | **{redteam['block_rate_pct']:.1f}%** ({redteam['blocked_count']}/{redteam['total_attacks']} blocked) | ≥ 85.0% |",
        f"| **p50 / p95 Execution Latency** | {v2_sim['latency_p50_ms']:.1f}ms / {v2_sim['latency_p95_ms']:.1f}ms (simulated) | **{v2_live['latency_p50_ms']:.1f}ms / {v2_live['latency_p95_ms']:.1f}ms** | — |",
        f"| **Mean Cost per Incident** | `${v2_sim['mean_cost_usd']:.4f}` (simulated) | **`${v2_live['mean_cost_usd']:.4f}`** (±`${v2_live['cost_std_usd']:.4f}`) | Cap: `$0.05` |",
        "",
        "### C. Scenario-by-Scenario Breakdown (`evals/results/v2-optimized.json` & `v2-live.json`)",
        "",
        "| Scenario ID | Difficulty | `v2-optimized` Acc (simulated) | `v2-optimized` p50 Latency | `v2-live` Acc (3 repeats) | `v2-live` Avg Latency |",
        "|---|---|---|---|---|---|",
    ]

    for sc_id in sorted(set(sim_by_scenario) | set(live_by_scenario)):
        s_row = sim_by_scenario.get(sc_id, {})
        l_rows = live_by_scenario.get(sc_id, [])
        diff = s_row.get("difficulty") or (l_rows[0].get("difficulty") if l_rows else "—")
        sim_acc = f"{s_row['accuracy']:.1f}" if "accuracy" in s_row else "—"
        sim_lat = f"{s_row['latency_ms']:.1f}ms" if "latency_ms" in s_row else "—"
        if l_rows:
            live_acc_avg = sum(r["accuracy"] for r in l_rows) / len(l_rows) * 100
            live_lat_avg = sum(r["latency_ms"] for r in l_rows) / len(l_rows)
            live_acc_str = f"{live_acc_avg:.0f}% ({len(l_rows)}/{len(l_rows)})" if live_acc_avg == 100 else f"{live_acc_avg:.1f}%"
            live_lat_str = f"{live_lat_avg:.1f}ms"
        else:
            live_acc_str = "—"
            live_lat_str = "—"
        lines.append(
            f"| `{sc_id}` | {diff} | {sim_acc} | {sim_lat} | {live_acc_str} | {live_lat_str} |"
        )

    lines.append("<!-- END_EVAL_TABLES -->")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    v2_sim = _load("v2-optimized.json")
    v2_live = _load("v2-live.json")
    redteam = _load("redteam_summary.json")
    retrieval = _load("retrieval_summary.json")

    content = README_PATH.read_text(encoding="utf-8")
    updated = re.sub(
        r"<!-- BEGIN_RETRIEVAL_STATS -->.*?<!-- END_RETRIEVAL_STATS -->",
        build_retrieval_block(retrieval),
        content,
        flags=re.DOTALL,
    )
    updated = re.sub(
        r"<!-- BEGIN_EVAL_TABLES -->.*?<!-- END_EVAL_TABLES -->",
        build_eval_block(v2_sim, v2_live, redteam),
        updated,
        flags=re.DOTALL,
    )

    if args.check:
        if updated != content:
            print("README.md generated sections are out of sync with evals/results/*.json", file=sys.stderr)
            return 1
        print("README.md generated sections match evals/results/*.json cleanly.")
        return 0

    README_PATH.write_text(updated, encoding="utf-8")
    print("Updated README.md from evals/results/*.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
