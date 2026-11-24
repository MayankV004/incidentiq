from evals.redteam.run_redteam import run_redteam_suite


def test_redteam_suite_outcome_based():
    results = run_redteam_suite()
    assert results["total_attacks"] == 20
    assert results["blocked_count"] == 20
    assert results["block_rate_pct"] == 100.0
    assert results["status"] == "PASSED"
