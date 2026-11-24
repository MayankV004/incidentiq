import json
import os

from evals.run_evals import run_benchmark


def test_eval_split_and_repeats():
    splits_file = "evals/splits.json"
    assert os.path.exists(splits_file), "splits.json must exist"

    with open(splits_file) as f:
        data = json.load(f)

    assert "dev" in data and "held_out" in data
    all_split_ids = data["dev"] + data["held_out"]
    assert len(all_split_ids) == 8
    assert len(set(all_split_ids)) == 8
    for sc_id in all_split_ids:
        assert os.path.isdir(os.path.join("scenarios", sc_id)), (
            f"Scenario '{sc_id}' in splits.json does not exist on disk"
        )

    out = run_benchmark(
        run_name="test_dev_3rep",
        repeats=3,
        split="dev",
        enforce_thresholds=False,
        delay_seconds=0.0,
    )
    assert out["total_scenarios"] == len(data["dev"])
    assert out["total_runs"] == len(data["dev"]) * 3
    assert out["repeats"] == 3
    assert out["split"] == "dev"
    assert out["code_path"] in ("deterministic_fallback", "real_llm_live")
    assert "accuracy_std_pct" in out
    assert "latency_std_ms" in out
    assert "cost_std_usd" in out

    test_out = os.path.join("evals", "results", "test_dev_3rep.json")
    if os.path.exists(test_out):
        os.remove(test_out)
