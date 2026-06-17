"""Candidate generation for cross-venue equivalence scans."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import combinations
from typing import TYPE_CHECKING

from prediction_desk.domain.models import Market
from prediction_desk.equivalence.models import (
    EquivalenceCandidate,
    compute_candidate_input_hash,
)
from prediction_desk.equivalence.text import extract_key_terms, token_jaccard_score

if TYPE_CHECKING:
    from prediction_desk.persistence.repositories import PredictionMarketRepository


def generate_equivalence_candidates(
    *,
    repo: PredictionMarketRepository,
    market_ids: list[str] | None,
    asof_timestamp: datetime,
    venue_names: list[str] | None = None,
    min_candidate_score: int = 40,
    max_pairs: int = 10000,
    allow_same_venue: bool = False,
    force: bool = False,
) -> list[EquivalenceCandidate]:
    markets = _candidate_markets(repo, market_ids, venue_names)
    candidates: list[EquivalenceCandidate] = []
    pair_count = 0
    for left, right in combinations(markets, 2):
        if not allow_same_venue and left.venue_id == right.venue_id:
            continue
        if pair_count >= max_pairs:
            break
        pair_count += 1
        left_event = repo.get_event(left.event_id)
        right_event = repo.get_event(right.event_id)
        candidate = _candidate(
            left,
            right,
            asof_timestamp,
            left_event.category if left_event else None,
            right_event.category if right_event else None,
        )
        if candidate.candidate_score < min_candidate_score:
            continue
        existing = repo.find_equivalence_candidate_by_hash(candidate.input_hash)
        if existing is not None and not force:
            candidates.append(existing)
            continue
        repo.save_equivalence_candidate(candidate)
        candidates.append(candidate)
    return candidates


def _candidate_markets(
    repo: PredictionMarketRepository,
    market_ids: list[str] | None,
    venue_names: list[str] | None,
) -> list[Market]:
    if market_ids:
        markets = [repo.get_market(market_id) for market_id in sorted(set(market_ids))]
        resolved = [market for market in markets if market is not None]
    else:
        resolved = repo.list_markets(limit=1000)
    if venue_names:
        venue_filter = {name.casefold() for name in venue_names}
        filtered: list[Market] = []
        for market in resolved:
            venue = repo.get_venue(market.venue_id)
            venue_name = venue.name.casefold() if venue is not None else market.venue_id.casefold()
            if venue_name in venue_filter or market.venue_id.casefold() in venue_filter:
                filtered.append(market)
        resolved = filtered
    return sorted(resolved, key=lambda market: (market.venue_id, market.market_id))


def _candidate(
    left: Market,
    right: Market,
    asof_timestamp: datetime,
    left_category: str | None,
    right_category: str | None,
) -> EquivalenceCandidate:
    title_score = token_jaccard_score(left.title, right.title)
    left_terms = set(extract_key_terms(left.title))
    right_terms = set(extract_key_terms(right.title))
    shared = sorted(left_terms & right_terms)
    category_match = (
        left_category is not None
        and right_category is not None
        and left_category == right_category
    )
    score = min(
        100,
        round((title_score * 0.85) + (10 if shared else 0) + (5 if category_match else 0)),
    )
    reasons: list[str] = []
    if title_score >= 70:
        reasons.append("TITLE_SIMILARITY_CANDIDATE")
    if shared:
        reasons.append("SHARED_KEY_TERMS")
    if left.venue_id != right.venue_id:
        reasons.append("CROSS_VENUE_PAIR")
    candidate = EquivalenceCandidate(
        candidate_id="pending",
        left_market_id=left.market_id,
        right_market_id=right.market_id,
        asof_timestamp=asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        candidate_score=score,
        candidate_reasons=sorted(set(reasons)),
        left_venue_id=left.venue_id,
        right_venue_id=right.venue_id,
        title_similarity_score=title_score,
        category_match=category_match,
        shared_tokens=shared,
        input_hash="pending",
        metadata={"candidate_generation": "title_event_key_term_v1"},
    )
    input_hash = compute_candidate_input_hash(candidate)
    return candidate.model_copy(
        update={
            "candidate_id": f"equivalence_candidate_{input_hash[:24]}",
            "input_hash": input_hash,
        }
    )
