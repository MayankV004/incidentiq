from evals.run_retrieval_eval import run_retrieval_evaluation


def test_knowledge_retrieval_benchmark():
    summary = run_retrieval_evaluation()
    assert summary["total_queries"] == 20
    assert summary["hit_at_3_pct"] >= 95.0, f"Hit@3 too low: {summary['hit_at_3_pct']}%"
    assert summary["mrr"] >= 0.90, f"MRR too low: {summary['mrr']}"
