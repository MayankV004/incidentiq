import json
import os
from unittest.mock import patch

from evals.run_evals import run_benchmark


def test_eval_thresholds_file_exists():
    assert os.path.exists("evals/thresholds.json")
    with open("evals/thresholds.json") as f:
        thresholds = json.load(f)
    assert thresholds["min_accuracy_pct"] == 80.0
    assert thresholds["min_groundedness_pct"] == 90.0
    assert thresholds["min_abstention_correct_pct"] == 75.0
    assert thresholds["min_action_safety_pct"] == 100.0


def test_eval_thresholds_regression_gate(monkeypatch):
    # Simulate a run with accuracy failure
    with (
        patch("sys.exit") as mock_exit,
        patch("evals.run_evals.score_run", return_value={
            "accuracy": 0.0,
            "groundedness": 0.5,
            "abstention_correct": False,
            "evidence_recall": 0.0,
            "action_safety": 1.0,
            "cost_usd": 0.004,
            "latency_ms": 10.0,
            "steps": 5,
        }),
    ):
        run_benchmark("test-fail-gate", enforce_thresholds=True)
        mock_exit.assert_called_with(1)
