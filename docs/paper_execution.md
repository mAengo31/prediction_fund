# Paper Execution Simulator v1

Paper Execution Simulator v1 evaluates hypothetical trade intents after the Pre-Trade Gate
and records SIMULATED orders, fills, ledger entries, positions, and portfolio snapshots.
It is not live trading, does not route orders, and does not connect to venue accounts.

## Purpose

The simulator tests admissibility and accounting mechanics against replay-safe market
data. It answers whether a hypothetical intent would have passed the gate and how a
conservative deterministic fill model would update a simulated ledger using data available
at or before the simulation timestamp.

## Models

`PaperExecutionPolicy` configures simulation behavior: simulated shorts, partial fills,
configurable simulated fee bps, required pre-trade actions, and the fill model.

`PaperOrder` is a simulated order object. It stores the trade intent, pre-trade decision,
policy, accepted size, filled size, status, and rejection reason codes. It is not a venue
order and has no venue order ID, account ID, wallet, or credential fields.

`PaperFill` records a simulated fill. `is_simulated` is always true. Fills reference
stored orderbook, price, and liquidity snapshots when available.

`PaperLedgerEntry` records simulated cash, fee, and position effects.

`PaperPositionSnapshot` stores simulated long-only position state, cost basis, average
entry price, and clearly labeled simulated realized and unrealized PnL fields.

`PaperPortfolioSnapshot` stores simulated cash, exposure, fees, equity, and mark-to-market
state across positions.

`PaperSimulationRun` and `PaperSimulationRunSummary` record run-once simulation batches
and aggregate simulated order, fill, and portfolio metrics.

## Fill Models

`IMMEDIATE_TOP_OF_BOOK` fills crossed aggressive or market-like intents against the best
available ask for BUY and best available bid for SELL. Size is capped by top-of-book
depth, with partial fills allowed by the default policy.

`IMMEDIATE_WALK_BOOK` walks visible book levels up to the limit price and requested size.

`PASSIVE_NO_FILL_V1` leaves accepted passive orders resting and unfilled.

`RESEARCH_NO_FILL` never creates immediate fills. Research-only intents are conservative
and do not create immediate fills.

## Fee Model

Fees are configurable simulated fees. The default policy uses zero fee bps. The fee helper
does not assert that any configured value matches a real venue schedule.

## Long-Only v1

By default, simulated SELL intents can only reduce an existing simulated long position.
Simulated shorting is blocked unless a paper policy explicitly enables it, and the default
policy does not.

## No-Lookahead

Fills use latest as-of orderbook data and market-data snapshots. Price, liquidity,
position, and portfolio as-of methods use `available_at <= asof_timestamp`. A venue
observation time alone never makes data usable for a simulated fill.

## Pre-Trade Dependency

Every simulated order calls Pre-Trade Gate v1 first. `NO_TRADE` and `MANUAL_REVIEW`
decisions are rejected by the default paper policy. `ALLOW_SMALLER_SIZE` reduces accepted
size. `PASSIVE_ONLY` only permits passive or research-safe intents under the default
policy.

## Limitations

V1 uses simple deterministic book-based fills and does not model queue priority, latency,
hidden liquidity, cancellations, settlement, real account positions, order routing, or
venue-specific execution rules. All outputs are SIMULATED.

## Later Support

This layer can later support richer execution simulator improvements, strategy replay,
risk attribution, execution management system design, and MiroFish slow-lane feature
snapshots.

Strategy Research Harness v1 can optionally call the paper simulator after a proposal
passes Pre-Trade Gate v1. The resulting paper order, fill, position, and portfolio objects
remain simulated and are linked through `ResearchDecisionTrace`.

See [strategy_research.md](strategy_research.md) for research signals, hypothetical
proposals, and simulated attribution.
