# Desk Decision Workbench v1

Desk Decision Workbench v1 is the first desk-facing review layer for prediction-desk. It
turns existing backend intelligence into review queues, market decision cards,
cross-venue comparison cards, and an internal review journal.

It is not live execution. It does not place orders, cancel orders, route orders, connect
to authenticated venue endpoints, use credentials, access wallets, or use private keys.
Workbench output is review context for a human desk operator.

## Purpose

The workbench answers operational questions:

- Why review this market now?
- What evidence supports the review priority?
- What does the latest pre-trade gate context allow or block?
- Which data gaps still affect interpretation?
- Which research, scenario, paper, integrity, equivalence, and divergence records are
  relevant as of the review timestamp?

All queue and card builders use existing repository as-of methods. Market data,
integrity, equivalence, divergence, pre-trade, paper, research, scenario, and gap context
must be available at or before the requested timestamp.

## Models

`DeskWatchlist` stores named desk watchlists. Defaults cover public-read Kalshi,
public-read Polymarket, high-priority review, data-gap review, divergence review, and
pretrade-blocked review.

`MarketReviewQueueItem` stores one market review queue entry with a 0-100 priority score,
a priority bucket, review status, primary reason code, supporting reason codes, and
source evidence IDs.

`MarketDecisionCard` aggregates the latest as-of state for one market: price, liquidity,
data quality, rule context, integrity, equivalence, divergence, pre-trade, simulated
paper state, research, scenario, and data gaps. Its recommended next action is a review
action, never a trade action.

`CrossVenueComparisonCard` aggregates equivalence and divergence context for one market
pair. It helps the desk review comparable-market context without making execution claims.

`DeskReviewNote` is an internal journal note linked to a market, queue item, decision
card, or comparison card. It is for observations, review decisions, risk notes, data
issues, and strategy notes. Do not store secrets in notes.

`WorkbenchRun` and `WorkbenchRunSummary` record synchronous queue/card build runs and
aggregate counts by priority, review action, and reason code.

## Queue Behavior

Queue priority is deterministic. Examples:

- data gaps raise data-gap review priority
- pre-trade `NO_TRADE` or `MANUAL_REVIEW` raises pre-trade review priority
- high integrity risk raises integrity review priority
- material or review-worthy divergence raises comparison review priority
- research signals that require review raise research review priority
- clean markets with no review context remain low or informational

The queue does not recommend live trades.

Data gaps are append-only audit rows. Queue and card scoring use gaps from the latest
relevant coverage report as of the workbench timestamp, rather than all historical gap
rows. This prevents an old missing-data gap from keeping a market at high review priority
after a newer coverage report has closed that gap.

## Decision Cards

Decision cards are compact, evidence-backed snapshots. They include source reference IDs
so an operator can inspect the underlying records. Paper and portfolio fields are clearly
simulated. PnL and equity fields retain simulated naming.

Review actions are:

- `REVIEW_CONTRACT`
- `REVIEW_DATA_GAP`
- `REVIEW_DIVERGENCE`
- `REVIEW_INTEGRITY`
- `REVIEW_PRETRADE_BLOCK`
- `REVIEW_RESEARCH_SIGNAL`
- `WATCH_ONLY`
- `NO_ACTION`

These are review actions only.

## API

Workbench endpoints are under `/api/v1/workbench` and use the existing bearer-token auth:

- `POST /workbench/runs`
- `GET /workbench/runs`
- `GET /workbench/runs/{workbench_run_id}`
- `GET /workbench/runs/{workbench_run_id}/summary`
- `POST /workbench/queues/build`
- `GET /workbench/queues/items`
- `POST /workbench/markets/{market_id}/decision-card`
- `GET /workbench/markets/{market_id}/decision-card/latest`
- `POST /workbench/equivalence/{equivalence_assessment_id}/comparison-card`
- `GET /workbench/comparison-cards`
- `POST /workbench/notes`
- `GET /workbench/notes`
- `GET /workbench/notes/{note_id}`

## CLI

```bash
prediction-desk workbench-build-queue --market-id mkt_cpi_yoy_at_least_3pct_2026_09
prediction-desk workbench-queue --limit 25
prediction-desk workbench-card --market-id mkt_cpi_yoy_at_least_3pct_2026_09
prediction-desk workbench-run --market-id mkt_cpi_yoy_at_least_3pct_2026_09
prediction-desk workbench-add-note \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --text "Reviewed data gap context."
prediction-desk workbench-notes --market-id mkt_cpi_yoy_at_least_3pct_2026_09
```

## Staging Smoke

After deploying to Azure staging and running migrations, validate the workbench API without
printing secrets:

```bash
API_BASE_URL="https://prediction-desk-staging-api.bluebush-22f9863f.centralus.azurecontainerapps.io" \
PREDICTION_DESK_API_TOKEN="<secret>" \
scripts/staging_workbench_smoke.sh
```

The script uses one existing staging market, builds a workbench run and review queue,
creates and reads a decision card, and writes a safe observation note:

`Staging validation note: workbench smoke completed. No trading action.`

It does not call public venue endpoints and does not perform execution.

## Prohibited

The workbench does not add:

- live trading
- order placement
- order cancellation
- order routing
- venue credentials
- wallets or private keys
- real account IDs
- real positions
- public-read scheduling
- MiroFish runtime execution
- LLM calls

Future UI work can build on these API and CLI surfaces without changing the execution
boundary.
