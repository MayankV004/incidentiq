import json
import os

from evals.run_evals import run_benchmark


def test_eval_split_and_repeats(tmp_path):
    splits_file = "evals/splits.json"
    assert os.path.exists(splits_file), "splits.json must exist"

    with open(splits_file) as f:
        data = json.load(f)

    assert "dev" in data and "held_out" in data
    assert len(data["dev"]) == 14
    assert len(data["held_out"]) == 6

    # Test running with dev split and 3 repeats in test mode
    out = run_benchmark(
        run_name="test_dev_3rep", repeats=3, split="dev", enforce_thresholds=False
    )
    assert out["total_runs"] == out["total_scenarios"] * 3
    assert out["repeats"] == 3
    assert out["split"] == "dev"
    assert out["code_path"] in ("deterministic_fallback", "real_llm_live")
    assert "accuracy_std_pct" in out
    assert "latency_std_ms" in out
    assert "cost_std_usd" in out

    # Clean up test output
    test_out = os.path.join("evals", "results", "test_dev_3rep.json")
    if os.path.exists(test_out):
        os.remove(test_out)
