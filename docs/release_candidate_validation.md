# Release Candidate Validation

Validation date: 2026-06-17T05:11:12Z

Commit hash validated: `815ab4c21de5387da7cb95ba0d6f74a8bf6176e1`

Note: validation was run against the current working tree, which contains the completed
Round 12 implementation plus this RC validation note and count-inspection script.

## Commands Run

```bash
python -m pytest
python -m ruff check .
python -m mypy
git diff --check
DATABASE_URL=sqlite:////tmp/prediction_desk_rc_sqlite.db scripts/migrate.sh
docker compose config
scripts/smoke_local.sh
scripts/smoke_docker.sh
TEST_DATABASE_URL=postgresql+psycopg://prediction_desk:prediction_desk@localhost:55432/prediction_desk python -m pytest -m postgres
```

Additional validation:

```bash
prediction-desk init-db --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk load-sample-data --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk ingest-fixtures --venue kalshi --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk ingest-fixtures --venue polymarket --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk market-data-derive --all --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk data-quality --all --asof 2026-06-16T12:45:00Z --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk analyze-rules --all --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk integrity-run --asof 2026-06-16T12:45:00Z --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk equivalence-run --asof 2026-06-16T12:20:00Z --market-id kalshi_market_kxweather_nyc_rain_20260930 --market-id polymarket_market_0xrainnycsep2026 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk divergence-run --asof 2026-06-16T12:20:00Z --market-id kalshi_market_kxweather_nyc_rain_20260930 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk pretrade-create-default-policy --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk paper-create-default-policy --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk research-create-default-strategies --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk pretrade-check --market-id mkt_sfo_rain_2026_09_01 --asof 2026-06-16T12:00:00Z --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk paper-simulate-intent --market-id mkt_sfo_rain_2026_09_01 --asof 2026-06-16T12:00:00Z --intent-type MARKET_LIKE --strategy-context RESEARCH --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk research-build-features --market-id mkt_sfo_rain_2026_09_01 --asof 2026-06-16T12:00:00Z --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk research-generate-signals --market-id mkt_sfo_rain_2026_09_01 --asof 2026-06-16T12:00:00Z --strategy-id research_strategy_baseline_research_only_v1 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk research-generate-proposals --market-id mkt_sfo_rain_2026_09_01 --asof 2026-06-16T12:00:00Z --strategy-id research_strategy_baseline_research_only_v1 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk research-evaluate-proposal --proposal-id research_proposal_ddfb9e5bfead7f391ccbf2f1 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk research-run --start 2026-06-16T12:00:00Z --end 2026-06-16T12:00:00Z --strategy-id research_strategy_baseline_research_only_v1 --market-id mkt_sfo_rain_2026_09_01 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk replay-run --policy trust_verdict_v1 --start 2026-06-16T12:00:00Z --end 2026-06-16T13:00:00Z --market-id mkt_sfo_rain_2026_09_01 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk replay-run --policy pretrade_gate_v1 --start 2026-06-16T12:00:00Z --end 2026-06-16T13:00:00Z --market-id mkt_sfo_rain_2026_09_01 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk replay-run --policy paper_sim_gate_v1 --start 2026-06-16T12:00:00Z --end 2026-06-16T13:00:00Z --market-id mkt_sfo_rain_2026_09_01 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
prediction-desk replay-run --policy research_policy_v1 --start 2026-06-16T12:00:00Z --end 2026-06-16T13:00:00Z --market-id mkt_sfo_rain_2026_09_01 --database-url sqlite:////tmp/prediction_desk_rc_cli.db
python scripts/inspect_db_counts.py --database-url sqlite:////tmp/prediction_desk_rc_cli.db --json
```

Focused no-lookahead test subset:

```bash
python -m pytest \
  tests/test_marketdata_service.py::test_asof_price_and_liquidity_use_available_at_not_observed_at \
  tests/test_replay_asof_repositories.py::test_asof_rule_snapshot_query_does_not_return_future_snapshot \
  tests/test_replay_asof_repositories.py::test_asof_orderbook_query_does_not_return_future_snapshot \
  tests/test_integrity_features.py::test_feature_snapshot_does_not_use_future_available_market_data \
  tests/test_integrity_features.py::test_feature_snapshot_does_not_use_future_rule_snapshot_or_diff \
  tests/test_equivalence_service.py::test_future_equivalence_assessment_not_returned_by_asof_lookup \
  tests/test_divergence_service.py::test_service_uses_only_asof_available_market_data \
  tests/test_divergence_service.py::test_future_divergence_assessment_not_returned_by_asof_lookup \
  tests/test_pretrade_exposure.py::test_exposure_snapshot_asof_lookup_does_not_use_future_snapshot \
  tests/test_pretrade_service.py::test_future_pretrade_decision_not_returned_by_asof_lookup \
  tests/test_paper_fills.py::test_future_orderbook_is_not_used_for_fill_at_t \
  tests/test_paper_portfolio.py::test_position_and_portfolio_asof_do_not_return_future_snapshots \
  tests/test_research_features.py::test_feature_builder_uses_only_asof_safe_objects \
  tests/test_research_features.py::test_research_feature_repository_asof_filter_excludes_future_rows
```

## Pass/Fail Summary

- Full pytest: pass, `243 passed, 5 skipped`.
- Ruff: pass after formatting the new count-inspection script.
- Mypy: pass, `Success: no issues found in 110 source files`.
- `git diff --check`: pass.
- SQLite Alembic migration: pass through `20260616_0011`.
- Docker Compose config: pass.
- Local smoke: pass.
- Docker smoke: pass, including Postgres migrations through `20260616_0011`.
- Postgres marker tests: pass, `5 passed, 243 deselected`.
- API validation on local FastAPI with migrated SQLite: pass.
- Focused no-lookahead subset: pass, `14 passed`.

## Database Table-Count Summary

Counts from the CLI validation database after one idempotence rerun:

```json
{
  "venues": 3,
  "events": 8,
  "markets": 8,
  "outcomes": 16,
  "market_rule_snapshots": 9,
  "resolution_predicates": 8,
  "ambiguity_assessments": 8,
  "orderbook_snapshots": 14,
  "market_price_snapshots": 15,
  "market_liquidity_snapshots": 14,
  "market_data_quality_reports": 8,
  "integrity_assessments": 6,
  "market_equivalence_assessments": 1,
  "cross_venue_divergence_assessments": 1,
  "pretrade_decisions": 4,
  "paper_orders": 4,
  "paper_fills": 1,
  "paper_position_snapshots": 2,
  "paper_portfolio_snapshots": 4,
  "research_strategy_definitions": 5,
  "research_feature_snapshots": 11,
  "research_signals": 4,
  "research_intent_proposals": 1,
  "research_decision_traces": 3,
  "research_runs": 2,
  "replay_runs": 4
}
```

## Idempotence Findings

Repeated default object creation stayed idempotent:

- `default_pretrade_policy` / `v1`: 1 row.
- `default_paper_execution_policy` / `v1`: 1 row.
- Default research strategy definitions: 5 rows.

No duplicate unchanged deterministic snapshots were found:

- Duplicate rule hashes by market: 0.
- Duplicate price hashes: 0.
- Duplicate liquidity hashes: 0.
- Duplicate research proposal hashes: 0.
- Duplicate research signal hashes: 0.
- Duplicate research feature hashes: 0.
- Duplicate integrity assessment hashes: 0.

Append-only behavior observed on the second same-database run:

- New integrity assessments when input context changed.
- New paper orders/position/portfolio snapshots from an additional simulated intent.
- New research traces/runs/signals/features when run context changed.

This is expected historical append behavior and did not corrupt deterministic hashes or
default-object uniqueness.

## No-Lookahead Findings

The focused subset proved:

- Market data uses `available_at`, not `observed_at`.
- Replay rule/orderbook lookups do not return future snapshots.
- Integrity features exclude future market data and future rule/diff context.
- Equivalence as-of lookup excludes future equivalence assessments.
- Divergence analysis excludes future market data and future assessments.
- Pre-trade exposure and decision lookups exclude future context.
- Paper fills do not use future orderbook data.
- Paper position/portfolio lookups exclude future snapshots.
- Research features and research list methods exclude future context.

## Research Attribution Findings

Research traces clearly link:

- proposal ID
- pre-trade decision ID
- paper order ID
- paper fill IDs
- pre-trade action
- simulated filled size

In the validation database, three research traces pointed to one deterministic proposal and
the same pre-trade decision ID; the associated paper orders kept the same pre-trade
decision reference. Trace-level attribution was understandable and did not count simulated
metrics as real performance.

The documentation now states that paper simulation independently enforces the pre-trade
gate invariant, while research summaries count proposal-to-pre-trade outcomes at the trace
level.

## Known Limitations

- The validated commit hash is the current `HEAD`; the working tree is not a clean
  committed release tag yet.
- Replay requires `start_time < end_time`; one-timestamp CLI replay checks need a later
  end time with an interval.
- Research strategies remain deterministic hypothesis tests, not production alpha models.
- Paper execution remains simulated-only and does not model queue position, latency,
  settlement, or real venue rules.
- MiroFish-style scenario features are only represented by a placeholder feature source.
- Manual public fetch remains explicit and disabled by default in tests and smoke paths.

## Safe Next Step

Round 13 can proceed to MiroFish / slow-lane scenario feature design after the Round 12
working tree is committed or otherwise checkpointed. The next round should consume
research feature interfaces rather than bypassing market-data, pre-trade, paper, or replay
as-of semantics.

## Still Prohibited

- Live trading.
- Real order placement or cancellation.
- Authenticated venue endpoints.
- Wallets, private keys, signing, or custody.
- Real account IDs or real positions.
- Execution adapters or cross-venue execution.
- Production alpha models.
- LLM calls in validation or CI.
- External network calls in tests or CI.
- Background daemons.

## Recommendation

Proceed to Round 13 after creating a release checkpoint for the current working tree. No
blocking RC validation failures remain.
