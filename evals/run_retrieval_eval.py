import json
import sys
from pathlib import Path

# Add repo root to python path
repo_root = Path(__file__).parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from incidentiq.rag.engine import HybridRAGEngine


def run_retrieval_evaluation(
    queries_path: str = "evals/retrieval_queries.json",
    output_path: str = "evals/results/retrieval_summary.json",
) -> dict:
    repo_root = Path(__file__).parents[1]
    q_file = repo_root / queries_path
    with open(q_file, "r", encoding="utf-8") as f:
        queries = json.load(f)

    engine = HybridRAGEngine(knowledge_dir=str(repo_root / "knowledge"))

    results_details = []
    hits_at_3 = 0
    reciprocal_ranks = []

    for item in queries:
        qid = item["query_id"]
        qtext = item["query"]
        srv = item.get("service", "")
        target = item["target_doc"]

        retrieved = engine.retrieve(query=qtext, service=srv, top_k=5)
        matched_rank = None
        for rank, chunk in enumerate(retrieved, start=1):
            if (
                chunk.chunk_id.startswith(f"doc_{target}_")
                or chunk.chunk_id == f"doc_{target}"
            ):
                matched_rank = rank
                break

        is_hit = matched_rank is not None and matched_rank <= 3
        if is_hit:
            hits_at_3 += 1

        rr = 1.0 / matched_rank if matched_rank is not None else 0.0
        reciprocal_ranks.append(rr)

        results_details.append(
            {
                "query_id": qid,
                "query": qtext,
                "service": srv,
                "target_doc": target,
                "matched_rank": matched_rank,
                "hit_at_3": is_hit,
                "reciprocal_rank": round(rr, 4),
                "top_chunks": [c.chunk_id for c in retrieved[:3]],
            }
        )

    n_queries = len(queries)
    hit_at_3_rate = hits_at_3 / n_queries if n_queries else 0.0
    mrr = sum(reciprocal_ranks) / n_queries if n_queries else 0.0

    summary = {
        "engine": "Okapi BM25 with Jaccard Lexical Overlap and Service Metadata Boosting",
        "total_queries": n_queries,
        "hit_at_3_count": hits_at_3,
        "hit_at_3_pct": round(hit_at_3_rate * 100.0, 2),
        "mrr": round(mrr, 4),
        "results": results_details,
    }

    out_file = repo_root / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=" * 60)
    print("KB RETRIEVAL BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total Evaluated Queries: {n_queries}")
    print(f"Hit@3: {summary['hit_at_3_pct']}% ({hits_at_3}/{n_queries})")
    print(f"MRR (Mean Reciprocal Rank): {summary['mrr']}")
    print(f"Summary written to: {out_file}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    run_retrieval_evaluation()
