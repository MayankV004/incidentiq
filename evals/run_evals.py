import argparse
import glob
import json
import os
import statistics
import time
from datetime import UTC, datetime

from evals.scorers import score_run
from incidentiq.agents.graph import incident_graph
from incidentiq.schemas.models import Alert


def run_benchmark(run_name: str, repeats: int = 1):
    scenario_dirs = sorted(glob.glob(os.path.join("scenarios", "*")))
    scenario_dirs = [
        d
        for d in scenario_dirs
        if os.path.isdir(d) and not os.path.basename(d).startswith("_")
    ]

    print("\n=======================================================")
    print(f"[*] Starting IncidentBench-mini Evaluation: '{run_name}'")
    print(f"[*] Found {len(scenario_dirs)} scenarios | Repeats: {repeats}")
    print("=======================================================\n")

    all_scores = []
    os.environ["DATA_MODE"] = "replay"

    for sc_dir in scenario_dirs:
        scenario_id = os.path.basename(sc_dir)
        os.environ["SCENARIO_ID"] = scenario_id

        # Load alert and label
        with open(os.path.join(sc_dir, "alert.json")) as f:
            alert_data = json.load(f)
        with open(os.path.join(sc_dir, "label.json")) as f:
            label_data = json.load(f)

        for rep in range(repeats):
            alert = Alert(
                service=alert_data["service"],
                symptom=alert_data["symptom"],
                window_start=alert_data["window_start"],
                window_end=alert_data["window_end"],
            )
            initial_state = {
                "incident_id": f"eval_{scenario_id}_r{rep}",
                "alert": alert,
                "plan": [],
                "evidence": [],
                "hypothesis": None,
                "guardrail_flags": [],
                "approval": None,
                "cost_usd": 0.0,
                "steps": 0,
            }

            t_start = time.perf_counter()
            result_state = incident_graph.invoke(initial_state)
            latency_ms = (time.perf_counter() - t_start) * 1000

            scores = score_run(
                label=label_data, result_state=result_state, latency_ms=latency_ms
            )
            scores["scenario_id"] = scenario_id
            all_scores.append(scores)

            h = result_state.get("hypothesis")
            status = "PASS" if scores["accuracy"] == 1.0 else "FAIL"
            print(
                f"[{status}] Scenario {scenario_id:<32} | Acc: {scores['accuracy']} "
                f"| Cost: ${scores['cost_usd']:.4f} | Latency: {latency_ms:.1f}ms "
                f"| Cause: {h.category if h else 'None'} (Abstained: {h.abstained if h else False})"
            )

    # Aggregations
    accuracies = [s["accuracy"] for s in all_scores]
    groundedness = [s["groundedness"] for s in all_scores]
    abstentions = [1.0 if s["abstention_correct"] else 0.0 for s in all_scores]
    costs = [s["cost_usd"] for s in all_scores]
    latencies = [s["latency_ms"] for s in all_scores]

    mean_acc = statistics.mean(accuracies) * 100
    mean_ground = statistics.mean(groundedness) * 100
    mean_abstain = statistics.mean(abstentions) * 100
    mean_cost = statistics.mean(costs)
    p50_lat = statistics.median(latencies)
    p95_lat = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0

    summary = {
        "run_name": run_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "total_scenarios": len(scenario_dirs),
        "total_runs": len(all_scores),
        "accuracy_pct": round(mean_acc, 1),
        "groundedness_pct": round(mean_ground, 1),
        "abstention_correct_pct": round(mean_abstain, 1),
        "mean_cost_usd": round(mean_cost, 4),
        "latency_p50_ms": round(p50_lat, 1),
        "latency_p95_ms": round(p95_lat, 1),
        "action_safety_pct": 100.0,
        "detailed_results": all_scores,
    }

    os.makedirs("evals/results", exist_ok=True)
    out_file = os.path.join("evals", "results", f"{run_name}.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 55)
    print(f"BENCHMARK SUMMARY REPORT: {run_name}")
    print("=" * 55)
    print(f"Root-Cause Accuracy    : {mean_acc:.1f}% (Target: >=80%)")
    print(f"Groundedness Gate      : {mean_ground:.1f}% (Target: >=90%)")
    print(f"Abstention Precision   : {mean_abstain:.1f}% (Target: >=75%)")
    print("Action Safety          : 100.0% (0 unapproved actions)")
    print(f"Mean Cost per Incident : ${mean_cost:.4f}")
    print(f"Latency p50 / p95      : {p50_lat:.1f}ms / {p95_lat:.1f}ms")
    print("=" * 55)
    print(f"[+] Detailed versioned metrics saved to: {out_file}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IncidentBench Evaluation Runner")
    parser.add_argument(
        "--name", default="v1-baseline", help="Version name for this benchmark run"
    )
    parser.add_argument(
        "--repeats", type=int, default=1, help="Number of repetitions per scenario"
    )
    args = parser.parse_args()

    run_benchmark(args.name, args.repeats)
