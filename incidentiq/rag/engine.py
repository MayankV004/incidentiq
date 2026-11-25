import glob
import math
import os
import re

from incidentiq.schemas.models import KBChunk


def tokenize_lexical(text: str) -> list[str]:
    """Tokenizes text into lowercase alphanumeric words for BM25/Jaccard scoring."""
    return re.findall(r"\w+", text.lower())


def score_lexical_texts(
    query: str,
    documents: list[tuple[str, str]],
    target_service: str = "",
    service_weight: float = 2.5,
) -> list[float]:
    """Computes combined Okapi BM25 + Jaccard + service boost scores for (service, text) docs."""
    if not documents:
        return []

    doc_token_list = [tokenize_lexical(doc_text) for _, doc_text in documents]
    avg_dl = (
        sum(len(d) for d in doc_token_list) / len(doc_token_list)
        if doc_token_list
        else 1.0
    )

    idf: dict[str, float] = {}
    n_docs = len(documents)
    query_terms = set(tokenize_lexical(query))
    query_tokens = tokenize_lexical(query)
    for term in query_terms:
        n_containing = sum(1 for doc in doc_token_list if term in doc)
        if n_containing > 0:
            idf[term] = math.log(
                (n_docs - n_containing + 0.5) / (n_containing + 0.5) + 1.0
            )

    k1 = 1.5
    b = 0.75
    scores: list[float] = []
    for idx, (doc_service, _) in enumerate(documents):
        doc_tokens = doc_token_list[idx]
        doc_len = len(doc_tokens)
        bm25 = 0.0
        for q in query_tokens:
            if q not in idf:
                continue
            freq = doc_tokens.count(q)
            numerator = freq * (k1 + 1)
            denominator = freq + k1 * (1 - b + b * (doc_len / (avg_dl or 1)))
            bm25 += idf[q] * (numerator / (denominator or 1))

        service_boost = (
            service_weight
            if target_service and doc_service.lower() == target_service.lower()
            else 0.0
        )
        q_set = set(query_tokens)
        c_set = set(doc_tokens)
        jaccard = len(q_set & c_set) / (len(q_set | c_set) or 1)
        scores.append((bm25 * 0.6) + (jaccard * 15.0) + service_boost)
    return scores


class HybridRAGEngine:
    """Lexical RAG Retrieval Engine combining Okapi BM25 ranking, token-level
    Jaccard overlap, and service metadata boosting for operational runbooks and postmortems.
    """

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = knowledge_dir
        self.chunks: list[KBChunk] = []
        self._load_and_chunk_documents()

    def _load_and_chunk_documents(self):
        """Reads all runbook and postmortem markdown files and segments them into semantic chunks."""
        doc_files = glob.glob(
            os.path.join(self.knowledge_dir, "**", "*.md"), recursive=True
        )
        for filepath in doc_files:
            filename = os.path.splitext(os.path.basename(filepath))[0]
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract title
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            doc_title = title_match.group(1) if title_match else filename

            # Extract metadata if available
            category_match = re.search(r"Category:\s*([a-zA-Z0-9_-]+)", content)
            category = category_match.group(1) if category_match else "general"

            service_match = re.search(r"Service:\s*([a-zA-Z0-9_-]+)", content)
            service = service_match.group(1) if service_match else "unknown"

            # Split into sections by Markdown headers (## )
            sections = re.split(r"\n(?=##\s+)", content)
            for idx, sec in enumerate(sections):
                sec = sec.strip()
                if not sec:
                    continue
                header_match = re.search(r"^##\s+(.+)$", sec, re.MULTILINE)
                section_title = (
                    header_match.group(1).lower().replace(" ", "_")
                    if header_match
                    else f"sec_{idx}"
                )
                clean_section = re.sub(r"[^a-z0-9_]", "", section_title)
                chunk_id = f"doc_{filename}_{clean_section}"

                self.chunks.append(
                    KBChunk(
                        chunk_id=chunk_id,
                        doc_title=f"{doc_title} ({section_title})",
                        category=category,
                        service=service,
                        content=sec,
                    )
                )

    def retrieve(self, query: str, service: str = "", top_k: int = 3) -> list[KBChunk]:
        """Retrieves top-k relevant knowledge chunks using Okapi BM25 scoring with Jaccard lexical overlap and service boosting."""
        if not self.chunks:
            return []

        docs = [(chunk.service, chunk.content) for chunk in self.chunks]
        scores = score_lexical_texts(query=query, documents=docs, target_service=service)
        candidate_scores = list(zip(scores, self.chunks, strict=True))

        # 3. Rerank and pick top K
        candidate_scores.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidate_scores[:top_k]

        results = []
        for score, chunk in top_candidates:
            res_chunk = chunk.model_copy()
            res_chunk.score = round(score, 3)
            results.append(res_chunk)

        return results


# Global singleton instance
_rag_engine: HybridRAGEngine | None = None


def get_rag_engine() -> HybridRAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = HybridRAGEngine()
    return _rag_engine
