"""Fuzzy name matching for partner/pair grading propagation."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

MATCH_CONFIDENT = 0.75
MATCH_MIN = 0.45


def normalize(s: str) -> str:
    s = str(s).lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"(.)\1{2,}", r"\1", s)


def score_match(query: str, candidate: str) -> float:
    p, n = normalize(query), normalize(candidate)
    n_tokens = n.split()
    tokens = [t for t in p.split() if len(t) > 1]
    if not tokens:
        return 0.0
    long_hits = sum(1 for t in tokens if len(t) > 2 and t in n_tokens)
    short_hits = sum(
        1 for t in tokens if len(t) <= 2 and any(nt.startswith(t) for nt in n_tokens)
    )
    token_score = (long_hits + short_hits) / len(tokens)
    return max(token_score * 0.9, SequenceMatcher(None, p, n).ratio() * 0.6)


def find_match(
    query: str, name_to_id: dict[str, int]
) -> tuple[int | None, str | None, float]:
    """Return (user_id, matched_name, score) for the best fuzzy match."""
    if not name_to_id:
        return None, None, 0.0
    scores = [(score_match(query, name), name, uid) for name, uid in name_to_id.items()]
    best_score, best_name, best_uid = max(scores, key=lambda x: x[0])
    if best_score >= MATCH_MIN:
        return best_uid, best_name, best_score
    return None, best_name, best_score
