#!/usr/bin/env python
"""Print read-only row counts for prediction-desk release-candidate tables."""

from __future__ import annotations

import argparse
import json

from sqlalchemy import func, select

from prediction_desk.persistence.database import build_engine
from prediction_desk.persistence.orm import Base

TABLES: tuple[str, ...] = (
    "venues",
    "events",
    "markets",
    "outcomes",
    "raw_venue_payloads",
    "market_rule_snapshots",
    "resolution_predicates",
    "ambiguity_assessments",
    "orderbook_snapshots",
    "market_price_snapshots",
    "market_liquidity_snapshots",
    "market_data_quality_reports",
    "integrity_assessments",
    "market_equivalence_assessments",
    "cross_venue_divergence_assessments",
    "pretrade_decisions",
    "paper_orders",
    "paper_fills",
    "paper_position_snapshots",
    "paper_portfolio_snapshots",
    "research_strategy_definitions",
    "research_feature_snapshots",
    "research_signals",
    "research_intent_proposals",
    "research_decision_traces",
    "research_runs",
    "replay_runs",
    "market_universe_definitions",
    "market_universe_members",
    "collection_plans",
    "collection_runs",
    "backfill_jobs",
    "backfill_segments",
    "data_coverage_reports",
    "data_gaps",
    "data_retention_policies",
)


def collect_counts(database_url: str | None = None) -> dict[str, int]:
    engine = build_engine(database_url)
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table_name in TABLES:
            table = Base.metadata.tables[table_name]
            count = connection.execute(select(func.count()).select_from(table)).scalar_one()
            counts[table_name] = int(count)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    args = parser.parse_args()

    counts = collect_counts(args.database_url)
    if args.json:
        print(json.dumps(counts, indent=2, sort_keys=True))
        return

    width = max(len(name) for name in counts)
    for table_name, count in counts.items():
        print(f"{table_name:<{width}}  {count}")


if __name__ == "__main__":
    main()
