"""Pure in-memory scoring and ranking for RAG retrieval.

No I/O — all functions operate on raw MongoDB documents (list[dict]) so they
can run safely inside asyncio.to_thread without blocking the event loop.

Retrieval types
───────────────
  basic      — cosine similarity between query embedding and stored embeddings
  mmr        — Maximal Marginal Relevance: relevance + diversity trade-off
  time_aware — bucket-based recency weighting combined with vector similarity
  hyde       — hypothetical document is generated upstream; arrives here as a
               pre-computed embedding, then basic scoring is applied

All scoring functions return list[ScoredDoc] = list[tuple[dict, float]].
Post-scoring helpers (threshold + sort) are separate so callers can compose.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity as _sk_cosine

    _SKLEARN = True
except ImportError:  # pragma: no cover
    _SKLEARN = False

# ─── Type alias ───────────────────────────────────────────────────────────────

ScoredDoc = tuple[dict, float]

# ─── Similarity helpers ───────────────────────────────────────────────────────


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors (pure Python)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _batch_cosine(query: list[float], vectors: list[list[float]]) -> list[float]:
    """Cosine similarity of query against every vector in vectors.

    Delegates to sklearn for batches larger than 10 when available (10–100x
    faster for typical RAG payloads), falls back to pure Python otherwise.
    """
    if not vectors:
        return []
    if _SKLEARN and len(vectors) > 10:
        arr = np.array(vectors, dtype=float)
        q = np.array(query, dtype=float).reshape(1, -1)
        return _sk_cosine(q, arr)[0].tolist()
    return [_cosine(query, v) for v in vectors]


# ─── Time bucket weighting ────────────────────────────────────────────────────

# (max_age_days, recency_weight) — ordered from newest to oldest
_TIME_BUCKETS: list[tuple[int, float]] = [
    (180, 1.0),   # 0–180 days
    (365, 0.9),   # 181–365 days
    (730, 0.8),   # 1–2 years
    (1095, 0.7),  # 2–3 years
]
_WEIGHT_OLDEST = 0.6  # 3+ years


def _time_weight(created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max(0, (now - created_at).days)
    for threshold, weight in _TIME_BUCKETS:
        if age_days <= threshold:
            return weight
    return _WEIGHT_OLDEST


def _parse_created_at(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


# ─── Metadata filter ──────────────────────────────────────────────────────────


def _matches_condition(metadata: dict[str, Any], condition: dict[str, Any]) -> bool:
    """Evaluate one Qdrant-style filter condition against a document's metadata."""
    key = condition.get("key", "")
    match_cfg = condition.get("match", {})
    if "value" in match_cfg:
        return metadata.get(key) == match_cfg["value"]
    if "any" in match_cfg:
        return metadata.get(key) in match_cfg["any"]
    if "text" in match_cfg:
        return match_cfg["text"].lower() in str(metadata.get(key, "")).lower()
    return False


def apply_metadata_filters(
    docs: list[dict],
    filters: dict[str, Any] | None,
) -> list[dict]:
    """Filter docs using Qdrant-style must / should / must_not conditions.

    Filter shape:
        {
            "must":     [{"key": "source", "match": {"value": "wiki"}}],
            "should":   [{"key": "tag",    "match": {"value": "urgent"}}],
            "must_not": [{"key": "status", "match": {"value": "archived"}}],
        }

    Rules:
      - must:     ALL conditions must be satisfied
      - should:   AT LEAST ONE condition must be satisfied (ignored when empty)
      - must_not: NONE of the conditions may be satisfied
    """
    if not filters:
        return docs

    must = filters.get("must", [])
    should = filters.get("should", [])
    must_not = filters.get("must_not", [])

    out: list[dict] = []
    for doc in docs:
        meta = doc.get("metadata", {})
        if must and not all(_matches_condition(meta, c) for c in must):
            continue
        if must_not and any(_matches_condition(meta, c) for c in must_not):
            continue
        if should and not any(_matches_condition(meta, c) for c in should):
            continue
        out.append(doc)
    return out


# ─── Scoring strategies ───────────────────────────────────────────────────────


def basic_score(docs: list[dict], query_vec: list[float]) -> list[ScoredDoc]:
    """Vector cosine similarity between query_vec and each doc's embedding."""
    embeddings = [doc.get("embedding") or [] for doc in docs]
    scores = _batch_cosine(query_vec, embeddings)
    return list(zip(docs, scores))


def mmr_score(
    docs: list[dict],
    query_vec: list[float],
    lambda_param: float,
    top_k: int,
) -> list[ScoredDoc]:
    """Maximal Marginal Relevance: balance relevance against redundancy.

    lambda_param=1.0 → pure relevance (equivalent to basic_score).
    lambda_param=0.0 → pure diversity.

    Algorithm:
      1. Score all candidates by cosine similarity to query.
      2. Fetch up to top_k×5 nearest candidates.
      3. Greedily pick the next doc that maximises:
           λ·relevance − (1−λ)·max_similarity_to_already_selected

    Falls back to basic_score when numpy / sklearn are unavailable.
    """
    if not _SKLEARN:
        return basic_score(docs, query_vec)

    embeddings = [doc.get("embedding") or [] for doc in docs]
    valid_pairs = [(d, e) for d, e in zip(docs, embeddings) if e]
    if not valid_pairs:
        return [(d, 0.0) for d in docs]

    valid_docs, valid_embs = zip(*valid_pairs)
    arr = np.array(valid_embs, dtype=float)
    q = np.array(query_vec, dtype=float).reshape(1, -1)
    query_scores: np.ndarray = _sk_cosine(q, arr)[0]

    candidate_count = min(top_k * 5, len(valid_docs))
    candidates: list[int] = query_scores.argsort()[::-1][:candidate_count].tolist()

    selected: list[int] = []
    while candidates and len(selected) < top_k:
        if not selected:
            best = max(candidates, key=lambda i: float(query_scores[i]))
        else:
            sel_arr = arr[selected]

            def _mmr_val(i: int, _sel=sel_arr) -> float:
                redundancy = float(_sk_cosine(arr[i].reshape(1, -1), _sel).max())
                return lambda_param * float(query_scores[i]) - (1 - lambda_param) * redundancy

            best = max(candidates, key=_mmr_val)

        selected.append(best)
        candidates.remove(best)

    return [(valid_docs[i], float(query_scores[i])) for i in selected]


def time_aware_score(
    docs: list[dict],
    query_vec: list[float],
    time_decay_factor: float,
) -> list[ScoredDoc]:
    """Bucket-based recency weighting combined with normalised vector similarity.

    Steps (matching reference implementation):
      1. Compute cosine similarity for each doc.
      2. Assign each doc to a time bucket based on its age.
      3. Within each bucket, min-max normalise the raw vector scores.
      4. Combine:  final = (1−decay)·normalised_vector + decay·bucket_weight
    """
    embeddings = [doc.get("embedding") or [] for doc in docs]
    raw_scores = _batch_cosine(query_vec, embeddings)

    # Group docs by their time bucket weight
    bucket_groups: dict[float, list[tuple[dict, float]]] = {}
    for doc, raw in zip(docs, raw_scores):
        created_at = _parse_created_at(doc.get("created_at"))
        weight = _time_weight(created_at) if created_at is not None else _WEIGHT_OLDEST
        bucket_groups.setdefault(weight, []).append((doc, raw))

    out: list[ScoredDoc] = []

    for bucket_weight, items in bucket_groups.items():
        scores = [s for _, s in items]
        lo, hi = min(scores), max(scores)

        for doc, raw in items:
            norm = (raw - lo) / (hi - lo) if hi != lo else 1.0
            final = max(0.0, min(1.0, (1 - time_decay_factor) * norm + time_decay_factor * bucket_weight))
            out.append((doc, final))

    return out


# ─── Post-scoring helpers ─────────────────────────────────────────────────────


def apply_score_threshold(scored: list[ScoredDoc], threshold: float) -> list[ScoredDoc]:
    """Remove any (doc, score) pair whose score is below threshold."""
    if threshold <= 0.0:
        return scored
    return [(doc, s) for doc, s in scored if s >= threshold]


def top_k_sorted(scored: list[ScoredDoc], top_k: int) -> list[ScoredDoc]:
    """Sort descending by score and return the top_k entries."""
    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]
