# Resolution Corpus v1

Prediction-market rule text is contract data, not metadata. The resolution corpus stores
the raw rule snapshot, a deterministic structured parse, dimension-level ambiguity scores,
evidence spans, and rule-to-rule diffs so later research can replay exactly what was known
at a point in time.

This v1 implementation is deterministic. It does not use LLM calls, venue APIs, external
network calls, private keys, wallets, or trading credentials.

Read-only fixture ingestion can create `MarketRuleSnapshot` objects from archived Kalshi
and Polymarket payloads. Those snapshots are then analyzed like any other stored rule
snapshot; the resolution corpus itself still does not call venues.

## Objects

`ResolutionSource` represents a canonical source that may settle a market, such as a
government release, regulator, venue, sports league, weather source, oracle, or manual
authority.

`ResolutionPredicate` is the structured parse of one `MarketRuleSnapshot`. It captures:

- Predicate type: binary event, scalar threshold, deadline, range, or unknown.
- Comparator and threshold where simple patterns are detected.
- Time-window fields and explicit time zone when present.
- Resolution source reference and settlement authority.
- Evidence spans with source text and character offsets when available.
- A stable normalized predicate string.

`AmbiguityAssessment` scores rule ambiguity by dimension:

- Source ambiguity.
- Temporal ambiguity.
- Definition ambiguity.
- Measurement ambiguity.
- Actor ambiguity.
- Threshold ambiguity.
- Dispute ambiguity.
- Exceptional-case ambiguity.
- Venue-adjudication ambiguity.

Scores use `0` for no detected ambiguity and `100` for maximum detected ambiguity. The
overall score is a transparent combination of the maximum dimension and average dimension:
`round(max_dimension * 0.6 + average_dimension * 0.4)`.

`RuleSnapshotDiff` compares two rule snapshots for the same market and records changed
text, changed terms, added and removed fragments, and semantic flags such as source,
authority, deadline, threshold, dispute-process, and material text changes.

## Deterministic v1 Limits

The parser is conservative and pattern based. It supports obvious threshold phrases,
simple percentages, dollar amounts, plain numeric units, clear month-day-year dates,
ISO-style dates, common US time-zone abbreviations, and source/authority phrases.

It intentionally does not perform heavy natural-language understanding. Missing parses are
stored as `PARTIAL` or `FAILED`, not guessed. This is preferable for replayable research:
future parser versions can be run against the same raw snapshots and compared explicitly.

## Use In The System

The corpus supports:

- Venue adapters later writing raw point-in-time rule snapshots before downstream analysis.
- Point-in-time backtesting using exact rule hashes, parsed predicates, ambiguity scores,
  and analysis model versions.
- Point-in-time replay by selecting only rule snapshots and resolution analysis available
  at or before each replay timestamp.
- Trust verdicts through resolution-risk scoring that can incorporate persisted ambiguity
  assessments.
- Cross-venue equivalence by comparing parsed predicates, resolution sources, settlement
  authority text, time windows, thresholds, time zones, and ambiguity profiles.
- Pre-trade gating in future systems by exposing deterministic rule-risk evidence without
  placing orders.
- MiroFish/scenario simulation later as a slow-lane feature generator that reads corpus
  artifacts; it is explicitly not part of this v1 implementation.

## Commands

Analyze latest rules:

```bash
prediction-desk analyze-rules --all
prediction-desk analyze-rules --market-id mkt_sfo_rain_2026_09_01
```

Diff the latest two rule snapshots:

```bash
prediction-desk diff-rule-snapshots --market-id mkt_rate_cut_rule_change_2026
```

## API

Resolution endpoints are under `/api/v1`:

- `POST /api/v1/markets/{market_id}/resolution/analyze-latest`
- `GET /api/v1/markets/{market_id}/resolution/latest`
- `GET /api/v1/rule-snapshots/{rule_snapshot_id}/resolution`
- `POST /api/v1/markets/{market_id}/rule-snapshots/diff-latest`

These endpoints analyze and persist deterministic artifacts from stored data only. They do
not call external APIs, trade, place orders, or create execution instructions.
