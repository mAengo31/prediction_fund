"""Command-line interface for local research workflows."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import typer

from prediction_desk.divergence.enums import DivergenceStatus
from prediction_desk.divergence.models import CrossVenueDivergenceRunConfig
from prediction_desk.divergence.runner import DivergenceRunError, run_divergence_scan
from prediction_desk.divergence.service import DivergenceService, DivergenceServiceError
from prediction_desk.equivalence.models import EquivalenceRunConfig
from prediction_desk.equivalence.runner import EquivalenceRunError, run_equivalence_scan
from prediction_desk.equivalence.service import EquivalenceService, EquivalenceServiceError
from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.ingestion.models import IngestionRun
from prediction_desk.ingestion.scheduler import run_ingestion_once
from prediction_desk.ingestion.service import IngestionService, IngestionServiceError
from prediction_desk.integrity.models import IntegrityRunConfig
from prediction_desk.integrity.runner import IntegrityRunError, run_integrity_scan
from prediction_desk.integrity.service import IntegrityService, IntegrityServiceError
from prediction_desk.marketdata.service import MarketDataService, MarketDataServiceError
from prediction_desk.paper.enums import PaperOrderStatus
from prediction_desk.paper.models import (
    PaperSimulateIntentRequest,
    PaperSimulationRunConfig,
    compute_trade_intent_from_request,
)
from prediction_desk.paper.runner import PaperRunError, run_paper_simulation
from prediction_desk.paper.service import PaperExecutionService, PaperServiceError
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import (
    ExposureSource,
    PreTradeAction,
    RestrictionScopeType,
    RestrictionType,
    StrategyContext,
    TradeIntentType,
    TradeSide,
)
from prediction_desk.pretrade.models import (
    ExposureSnapshotCreate,
    MarketRestrictionRuleCreate,
    PreTradeRunConfig,
    TradeIntent,
    compute_trade_intent_id,
)
from prediction_desk.pretrade.runner import PreTradeRunError, run_pretrade_checks
from prediction_desk.pretrade.service import PreTradeService, PreTradeServiceError
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.runner import ReplayError
from prediction_desk.replay.service import ReplayService
from prediction_desk.research.models import ResearchRunConfig
from prediction_desk.research.runner import ResearchRunError, run_research_simulation
from prediction_desk.research.service import ResearchService, ResearchServiceError
from prediction_desk.resolution.service import ResolutionCorpusError, ResolutionCorpusService
from prediction_desk.scoring.trust_verdict import build_trust_verdict

app = typer.Typer(no_args_is_help=True)
DECIMAL_ZERO = Decimal("0")
DECIMAL_ONE = Decimal("1")


@app.command("init-db")
def init_db_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to initialize.")
    ] = None,
) -> None:
    """Initializes the local database schema."""

    init_db(database_url)
    typer.echo("Initialized database.")


@app.command("load-sample-data")
def load_sample_data_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to write.")
    ] = None,
) -> None:
    """Loads deterministic sample markets into the database."""

    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        bundles = load_sample_data(repo)
    typer.echo(f"Loaded {len(bundles)} sample markets.")


@app.command("score-sample-markets")
def score_sample_markets_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to write.")
    ] = None,
) -> None:
    """Loads sample markets, computes trust verdicts, and prints a compact table."""

    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    asof_timestamp = datetime.now(tz=UTC)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        bundles = load_sample_data(repo)
        rows: list[tuple[str, str, int, int, str, str]] = []
        for bundle in bundles:
            verdict = build_trust_verdict(
                market=bundle.market,
                rule_snapshot=bundle.rule_snapshot,
                orderbook_snapshot=bundle.orderbook_snapshot,
                asof_timestamp=asof_timestamp,
            )
            repo.save_trust_verdict(verdict)
            rows.append(
                (
                    bundle.market.market_id,
                    bundle.market.title,
                    verdict.resolution_risk_score,
                    verdict.liquidity_risk_score,
                    verdict.action.value,
                    ",".join(verdict.reason_codes),
                )
            )

    _print_table(
        headers=(
            "market_id",
            "title",
            "resolution_risk_score",
            "liquidity_risk_score",
            "action",
            "reason_codes",
        ),
        rows=rows,
    )


@app.command("analyze-rules")
def analyze_rules_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
    market_id: Annotated[
        str | None, typer.Option("--market-id", help="Analyze the latest rule for one market.")
    ] = None,
    all_markets: Annotated[
        bool, typer.Option("--all", help="Analyze latest rules for all markets.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Recompute even when persisted analysis exists.")
    ] = False,
) -> None:
    """Analyzes market rules into persisted resolution-corpus artifacts."""

    if market_id is None and not all_markets:
        typer.echo("Provide --market-id or --all.", err=True)
        raise typer.Exit(1)

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    rows: list[tuple[str, str, str, str, int, str]] = []
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ResolutionCorpusService(repo)
        market_ids = [market_id] if market_id else [
            market.market_id for market in repo.list_markets(limit=500)
        ]
        for current_market_id in market_ids:
            if current_market_id is None:
                continue
            try:
                analysis = service.analyze_latest_rule_snapshot(current_market_id, force=force)
            except ResolutionCorpusError as exc:
                rows.append((current_market_id, "", "ERROR", "UNKNOWN", 100, exc.code))
                continue
            rows.append(
                (
                    analysis.market.market_id,
                    analysis.rule_snapshot.rule_snapshot_id,
                    analysis.predicate.parse_status.value,
                    analysis.predicate.predicate_type.value,
                    analysis.ambiguity_assessment.overall_score,
                    ",".join(analysis.ambiguity_assessment.reason_codes),
                )
            )

    _print_table(
        headers=(
            "market_id",
            "rule_snapshot_id",
            "parse_status",
            "predicate_type",
            "ambiguity_score",
            "reason_codes",
        ),
        rows=rows,
    )


@app.command("diff-rule-snapshots")
def diff_rule_snapshots_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market to diff.")],
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Diffs the latest two rule snapshots for a market."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ResolutionCorpusService(repo)
        try:
            diff = service.diff_latest_two_rule_snapshots(market_id)
        except ResolutionCorpusError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "market_id",
            "from_snapshot",
            "to_snapshot",
            "semantic_change_flags",
            "changed_terms",
        ),
        rows=[
            (
                diff.market_id,
                diff.from_rule_snapshot_id,
                diff.to_rule_snapshot_id,
                ",".join(diff.semantic_change_flags),
                ",".join(diff.changed_terms),
            )
        ],
    )


@app.command("replay-run")
def replay_run_command(
    start: Annotated[str, typer.Option("--start", help="Inclusive replay start timestamp.")],
    end: Annotated[str, typer.Option("--end", help="Inclusive replay end timestamp.")],
    policy: Annotated[
        str,
        typer.Option("--policy", help="Replay policy name."),
    ] = "trust_verdict_v1",
    interval_seconds: Annotated[
        int, typer.Option("--interval-seconds", help="Replay interval in seconds.")
    ] = 3600,
    market_ids: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID to include. Can be repeated."),
    ] = None,
    max_steps: Annotated[int, typer.Option("--max-steps", help="Maximum replay steps.")] = 10000,
    name: Annotated[str | None, typer.Option("--name", help="Replay run name.")] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs a point-in-time admissibility replay."""

    config = ReplayRunConfig(
        name=name,
        policy_name=policy,
        start_time=_parse_datetime(start),
        end_time=_parse_datetime(end),
        interval_seconds=interval_seconds,
        market_ids=market_ids,
        max_steps=max_steps,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = ReplayService(repo).run(config)
        except ReplayError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "policy",
            "total_steps",
            "no_trade_rate",
            "manual_review_rate",
            "passive_only_rate",
            "allow_rate",
            "errored_steps",
        ),
        rows=[
            (
                result.run.run_id,
                result.run.policy_name,
                result.summary.total_steps,
                result.summary.no_trade_rate,
                result.summary.manual_review_rate,
                result.summary.passive_only_rate,
                result.summary.allow_rate,
                result.summary.errored_steps,
            )
        ],
    )


@app.command("replay-summary")
def replay_summary_command(
    run_id: Annotated[str, typer.Option("--run-id", help="Replay run ID.")],
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints a stored replay summary."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            summary = ReplayService(repo).get_summary(run_id)
        except ReplayError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "total_steps",
            "no_trade_rate",
            "manual_review_rate",
            "passive_only_rate",
            "allow_rate",
            "errored_steps",
        ),
        rows=[
            (
                summary.run_id,
                summary.total_steps,
                summary.no_trade_rate,
                summary.manual_review_rate,
                summary.passive_only_rate,
                summary.allow_rate,
                summary.errored_steps,
            )
        ],
    )


@app.command("replay-steps")
def replay_steps_command(
    run_id: Annotated[str, typer.Option("--run-id", help="Replay run ID.")],
    limit: Annotated[int, typer.Option("--limit", help="Maximum steps to print.")] = 50,
    offset: Annotated[int, typer.Option("--offset", help="Step offset.")] = 0,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints stored replay steps."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            steps = ReplayService(repo).list_steps(run_id, limit=limit, offset=offset)
        except ReplayError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "asof_timestamp",
            "market_id",
            "action",
            "allowed_size_multiplier",
            "resolution_risk_score",
            "liquidity_risk_score",
            "reason_codes",
        ),
        rows=[
            (
                step.asof_timestamp.isoformat(),
                step.market_id,
                step.action,
                step.allowed_size_multiplier,
                step.resolution_risk_score,
                step.liquidity_risk_score,
                ",".join(step.reason_codes),
            )
            for step in steps
        ],
    )


@app.command("ingest-fixtures")
def ingest_fixtures_command(
    venue: Annotated[
        str,
        typer.Option("--venue", help="Venue to ingest: kalshi, polymarket, or all."),
    ],
    fixture_dir: Annotated[
        str | None,
        typer.Option("--fixture-dir", help="Optional fixture directory for a single venue."),
    ] = None,
    captured_at: Annotated[
        str | None,
        typer.Option("--captured-at", help="Optional ISO capture timestamp override."),
    ] = None,
    analyze_rules: Annotated[
        bool,
        typer.Option("--analyze-rules/--no-analyze-rules", help="Analyze ingested rules."),
    ] = True,
    recompute_verdicts: Annotated[
        bool,
        typer.Option(
            "--recompute-verdicts/--no-recompute-verdicts",
            help="Recompute trust verdicts for ingested markets.",
        ),
    ] = True,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Ingest committed fixture payloads into canonical prediction-desk objects."""

    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    venues = ["kalshi", "polymarket"] if venue.lower() == "all" else [venue.lower()]
    rows: list[tuple[str, str, str, int, int, int, int, int]] = []
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = IngestionService(repo)
        for current_venue in venues:
            try:
                result = service.ingest_fixture_payloads(
                    venue_name=current_venue,
                    fixture_dir=Path(fixture_dir) if fixture_dir else None,
                    captured_at=_parse_datetime(captured_at) if captured_at else None,
                    analyze_rules=analyze_rules,
                    recompute_verdicts=recompute_verdicts,
                )
            except IngestionServiceError as exc:
                typer.echo(exc.code, err=True)
                raise typer.Exit(1) from exc
            rows.append(_ingestion_run_row(result.run))

    _print_table(
        headers=(
            "run_id",
            "venue",
            "status",
            "payloads_archived",
            "markets_created",
            "rule_snapshots_created",
            "orderbook_snapshots_created",
            "errors_count",
        ),
        rows=rows,
    )


@app.command("ingest-public-sample")
def ingest_public_sample_command(
    venue: Annotated[str, typer.Option("--venue", help="Venue to fetch: kalshi or polymarket.")],
    limit: Annotated[int, typer.Option("--limit", help="Maximum public markets to fetch.")] = 10,
    allow_network: Annotated[
        bool,
        typer.Option("--allow-network", help="Required opt-in for public read-only GETs."),
    ] = False,
    analyze_rules: Annotated[
        bool,
        typer.Option("--analyze-rules/--no-analyze-rules", help="Analyze ingested rules."),
    ] = True,
    recompute_verdicts: Annotated[
        bool,
        typer.Option(
            "--recompute-verdicts/--no-recompute-verdicts",
            help="Recompute trust verdicts for ingested markets.",
        ),
    ] = True,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Manually fetch a small read-only public market sample."""

    if not allow_network:
        typer.echo("Public sample ingestion requires --allow-network.", err=True)
        raise typer.Exit(1)
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = IngestionService(repo).ingest_public_market_sample(
                venue_name=venue,
                limit=limit,
                allow_network=allow_network,
                analyze_rules=analyze_rules,
                recompute_verdicts=recompute_verdicts,
            )
        except IngestionServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "venue",
            "status",
            "payloads_archived",
            "markets_created",
            "rule_snapshots_created",
            "orderbook_snapshots_created",
            "errors_count",
        ),
        rows=[_ingestion_run_row(result.run)],
    )


@app.command("ingestion-runs")
def ingestion_runs_command(
    venue: Annotated[str | None, typer.Option("--venue", help="Optional venue filter.")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum runs to print.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Print stored ingestion runs."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        runs = IngestionService(repo).list_runs(venue_name=venue, limit=limit)

    _print_table(
        headers=(
            "run_id",
            "venue",
            "status",
            "payloads_archived",
            "markets_created",
            "errors_count",
        ),
        rows=[
            (
                run.ingestion_run_id,
                run.venue_name,
                run.status.value,
                run.payloads_archived,
                run.markets_created,
                run.errors_count,
            )
            for run in runs
        ],
    )


@app.command("venue-mappings")
def venue_mappings_command(
    venue: Annotated[str | None, typer.Option("--venue", help="Optional venue filter.")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum mappings to print.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Print stored external-to-canonical venue mappings."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        mappings = repo.list_venue_market_mappings(venue_name=venue, limit=limit)

    _print_table(
        headers=("venue", "external_market_id", "canonical_market_id", "status"),
        rows=[
            (
                mapping.venue_name,
                mapping.external_market_id,
                mapping.canonical_market_id or "",
                mapping.status.value,
            )
            for mapping in mappings
        ],
    )


@app.command("market-data-derive")
def market_data_derive_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
    market_id: Annotated[
        str | None, typer.Option("--market-id", help="Market ID to derive.")
    ] = None,
    all_markets: Annotated[
        bool, typer.Option("--all", help="Derive for all markets.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Persist snapshots even if matching hashes exist.")
    ] = False,
) -> None:
    """Derives canonical price and liquidity snapshots from stored orderbooks."""

    if market_id is None and not all_markets:
        typer.echo("Provide --market-id or --all.", err=True)
        raise typer.Exit(1)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = MarketDataService(repo)
        try:
            result = (
                service.derive_market_data_for_all_markets(force=force)
                if all_markets
                else service.derive_market_data_for_market(str(market_id), force=force)
            )
        except MarketDataServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=("market_id", "price_snapshots_created", "liquidity_snapshots_created"),
        rows=[
            (
                result.market_id or "all",
                result.price_snapshots_created,
                result.liquidity_snapshots_created,
            )
        ],
    )


@app.command("market-data-latest")
def market_data_latest_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints the latest as-of canonical market-data snapshot IDs."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            latest = MarketDataService(repo).get_latest_market_data_asof(
                market_id,
                _parse_datetime(asof) if asof else datetime.now(tz=UTC),
            )
        except MarketDataServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=("market_id", "price_snapshot_id", "liquidity_snapshot_id", "quality_score"),
        rows=[
            (
                latest.market_id,
                latest.price_snapshot.price_snapshot_id if latest.price_snapshot else "",
                (
                    latest.liquidity_snapshot.liquidity_snapshot_id
                    if latest.liquidity_snapshot
                    else ""
                ),
                latest.quality_report.quality_score if latest.quality_report else "",
            )
        ],
    )


@app.command("market-data-prices")
def market_data_prices_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    limit: Annotated[int, typer.Option("--limit", help="Maximum rows.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints canonical price snapshots."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        snapshots = MarketDataService(repo).list_price_snapshots(market_id, limit=limit)

    _print_table(
        headers=("available_at", "market_id", "source", "price", "bid", "ask", "mid"),
        rows=[
            (
                snapshot.available_at.isoformat(),
                snapshot.market_id,
                snapshot.source.value,
                snapshot.price or "",
                snapshot.bid or "",
                snapshot.ask or "",
                snapshot.mid or "",
            )
            for snapshot in snapshots
        ],
    )


@app.command("data-quality")
def data_quality_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
    market_id: Annotated[
        str | None, typer.Option("--market-id", help="Market ID to score.")
    ] = None,
    all_markets: Annotated[
        bool, typer.Option("--all", help="Compute quality for all markets.")
    ] = False,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
) -> None:
    """Computes and prints compact market-data quality reports."""

    if market_id is None and not all_markets:
        typer.echo("Provide --market-id or --all.", err=True)
        raise typer.Exit(1)
    asof_timestamp = _parse_datetime(asof) if asof else datetime.now(tz=UTC)
    rows: list[tuple[str, int, str, object, str]] = []
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = MarketDataService(repo)
        market_ids = (
            [market.market_id for market in repo.list_markets(limit=500)]
            if all_markets
            else [str(market_id)]
        )
        for current_market_id in market_ids:
            try:
                report = service.compute_market_data_quality(current_market_id, asof_timestamp)
            except MarketDataServiceError as exc:
                rows.append((current_market_id, 0, "ERROR", "", exc.code))
                continue
            rows.append(
                (
                    report.market_id,
                    report.quality_score,
                    report.severity.value,
                    report.freshness_seconds if report.freshness_seconds is not None else "",
                    ",".join(report.reason_codes),
                )
            )

    _print_table(
        headers=("market_id", "quality_score", "severity", "freshness_seconds", "reason_codes"),
        rows=rows,
    )


@app.command("ingestion-run-once")
def ingestion_run_once_command(
    venue: Annotated[
        str,
        typer.Option("--venue", help="Venue to ingest: kalshi, polymarket, or all."),
    ],
    mode: Annotated[
        str,
        typer.Option("--mode", help="fixture or manual_public_fetch."),
    ] = "fixture",
    limit: Annotated[int, typer.Option("--limit", help="Maximum public markets.")] = 10,
    allow_network: Annotated[
        bool, typer.Option("--allow-network", help="Required for manual public fetch.")
    ] = False,
    analyze_rules: Annotated[
        bool,
        typer.Option("--analyze-rules/--no-analyze-rules", help="Analyze rules."),
    ] = True,
    recompute_verdicts: Annotated[
        bool,
        typer.Option("--recompute-verdicts/--no-recompute-verdicts", help="Recompute verdicts."),
    ] = True,
    derive_market_data: Annotated[
        bool,
        typer.Option(
            "--derive-market-data/--no-derive-market-data",
            help="Derive canonical market-data snapshots.",
        ),
    ] = True,
    compute_quality: Annotated[
        bool,
        typer.Option("--compute-quality/--no-compute-quality", help="Compute data quality."),
    ] = True,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs one ingestion job suitable for cron or deployment jobs."""

    if mode == "manual_public_fetch" and not allow_network:
        typer.echo("manual_public_fetch requires --allow-network.", err=True)
        raise typer.Exit(1)
    init_db(database_url)
    venues = ["kalshi", "polymarket"] if venue.lower() == "all" else [venue.lower()]
    rows: list[tuple[str, str, str, int, int, int, int, int]] = []
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        for current_venue in venues:
            try:
                result = run_ingestion_once(
                    venue_name=current_venue,
                    mode=mode,
                    limit=limit,
                    allow_network=allow_network,
                    analyze_rules=analyze_rules,
                    recompute_verdicts=recompute_verdicts,
                    derive_market_data=derive_market_data,
                    compute_quality=compute_quality,
                    repo=repo,
                )
            except IngestionServiceError as exc:
                typer.echo(exc.code, err=True)
                raise typer.Exit(1) from exc
            rows.append(
                (
                    result.ingestion.run.ingestion_run_id,
                    result.ingestion.run.venue_name,
                    result.ingestion.run.status.value,
                    result.ingestion.run.payloads_archived,
                    result.price_snapshots_created,
                    result.liquidity_snapshots_created,
                    result.quality_reports_created,
                    len(result.cursors),
                )
            )

    _print_table(
        headers=(
            "run_id",
            "venue",
            "status",
            "payloads_archived",
            "price_snapshots_created",
            "liquidity_snapshots_created",
            "quality_reports_created",
            "cursors",
        ),
        rows=rows,
    )


@app.command("ingestion-cursors")
def ingestion_cursors_command(
    venue: Annotated[str | None, typer.Option("--venue", help="Optional venue filter.")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum cursors to print.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints stored run-once ingestion cursors."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        cursors = repo.list_ingestion_cursors(venue_name=venue, limit=limit)

    _print_table(
        headers=("cursor_id", "venue", "endpoint_type", "canonical_market_id", "status"),
        rows=[
            (
                cursor.cursor_id,
                cursor.venue_name,
                cursor.endpoint_type,
                cursor.canonical_market_id or "",
                cursor.status.value,
            )
            for cursor in cursors
        ],
    )


@app.command("integrity-analyze")
def integrity_analyze_command(
    market_ids: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID to analyze. Can be repeated."),
    ] = None,
    all_markets: Annotated[
        bool, typer.Option("--all", help="Analyze all markets up to --max-markets.")
    ] = False,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Recompute existing hashes.")] = False,
    max_markets: Annotated[
        int, typer.Option("--max-markets", help="Maximum markets when using --all.")
    ] = 100,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Analyzes fast-lane integrity signals for one or more markets."""

    if not all_markets and not market_ids:
        typer.echo("Provide --market-id or --all.", err=True)
        raise typer.Exit(1)
    asof_timestamp = _parse_datetime(asof) if asof else datetime.now(tz=UTC)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = IntegrityService(repo)
        target_market_ids = (
            [market.market_id for market in repo.list_markets(limit=max_markets)]
            if all_markets
            else list(market_ids or [])
        )
        rows: list[tuple[str, str, int, str, str, str]] = []
        for current_market_id in target_market_ids:
            try:
                assessment = service.analyze_market_integrity(
                    current_market_id,
                    asof_timestamp,
                    force=force,
                )
            except IntegrityServiceError as exc:
                rows.append(
                    (current_market_id, asof_timestamp.isoformat(), 100, "ERROR", "", exc.code)
                )
                continue
            rows.append(
                (
                    assessment.market_id,
                    assessment.asof_timestamp.isoformat(),
                    assessment.overall_risk_score,
                    assessment.severity.value,
                    assessment.action_hint.value,
                    ",".join(assessment.reason_codes),
                )
            )

    _print_table(
        headers=(
            "market_id",
            "asof_timestamp",
            "overall_risk_score",
            "severity",
            "action_hint",
            "reason_codes",
        ),
        rows=rows,
    )


@app.command("integrity-run")
def integrity_run_command(
    name: Annotated[str | None, typer.Option("--name", help="Run name.")] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Single as-of timestamp.")] = None,
    start: Annotated[str | None, typer.Option("--start", help="Range start timestamp.")] = None,
    end: Annotated[str | None, typer.Option("--end", help="Range end timestamp.")] = None,
    interval_seconds: Annotated[
        int | None, typer.Option("--interval-seconds", help="Historical interval seconds.")
    ] = None,
    market_ids: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID to include. Can be repeated."),
    ] = None,
    max_steps: Annotated[int, typer.Option("--max-steps", help="Maximum scan steps.")] = 10000,
    force: Annotated[bool, typer.Option("--force", help="Recompute existing hashes.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs a synchronous integrity scan."""

    config = IntegrityRunConfig(
        name=name,
        asof_timestamp=_parse_datetime(asof) if asof else None,
        start_time=_parse_datetime(start) if start else None,
        end_time=_parse_datetime(end) if end else None,
        interval_seconds=interval_seconds,
        market_ids=market_ids,
        max_steps=max_steps,
        force=force,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = run_integrity_scan(config, repo=repo)
        except IntegrityRunError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "total_assessments",
            "total_signals",
            "no_trade_rate",
            "manual_review_rate",
            "passive_only_rate",
            "markets_scanned",
        ),
        rows=[
            (
                result.run.integrity_run_id,
                result.summary.total_assessments,
                result.summary.total_signals,
                result.summary.no_trade_rate,
                result.summary.manual_review_rate,
                result.summary.passive_only_rate,
                result.summary.markets_scanned,
            )
        ],
    )


@app.command("integrity-latest")
def integrity_latest_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints the latest persisted integrity assessment for a market."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            assessment = IntegrityService(repo).get_latest_integrity_assessment(
                market_id,
                _parse_datetime(asof) if asof else None,
            )
        except IntegrityServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=("market_id", "asof_timestamp", "overall_risk_score", "severity", "action_hint"),
        rows=[
            (
                assessment.market_id,
                assessment.asof_timestamp.isoformat(),
                assessment.overall_risk_score,
                assessment.severity.value,
                assessment.action_hint.value,
            )
        ],
    )


@app.command("integrity-signals")
def integrity_signals_command(
    market_id: Annotated[
        str | None,
        typer.Option("--market-id", help="Optional market ID."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum signals to print.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints persisted integrity signals."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        signals = IntegrityService(repo).list_integrity_signals(
            market_id=market_id,
            limit=limit,
        )

    _print_table(
        headers=("asof_timestamp", "market_id", "signal_name", "severity", "score", "reason_code"),
        rows=[
            (
                signal.asof_timestamp.isoformat(),
                signal.market_id,
                signal.signal_name,
                signal.severity.value,
                signal.score,
                signal.reason_code,
            )
            for signal in signals
        ],
    )


@app.command("equivalence-assess")
def equivalence_assess_command(
    left_market_id: Annotated[
        str, typer.Option("--left-market-id", help="Left market ID.")
    ],
    right_market_id: Annotated[
        str, typer.Option("--right-market-id", help="Right market ID.")
    ],
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Recompute existing hashes.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Assesses deterministic contract equivalence for a market pair."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            response = EquivalenceService(repo).assess_market_equivalence(
                left_market_id,
                right_market_id,
                _parse_datetime(asof) if asof else datetime.now(tz=UTC),
                force=force,
            )
        except EquivalenceServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    assessment = response.assessment
    _print_table(
        headers=(
            "left_market_id",
            "right_market_id",
            "status",
            "permission",
            "overall_score",
            "confidence_score",
            "reason_codes",
        ),
        rows=[
            (
                assessment.left_market_id,
                assessment.right_market_id,
                assessment.status.value,
                assessment.comparison_permission.value,
                assessment.overall_score,
                assessment.confidence_score,
                ",".join(assessment.reason_codes),
            )
        ],
    )


@app.command("equivalence-candidates")
def equivalence_candidates_command(
    market_ids: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID to include. Can be repeated."),
    ] = None,
    venues: Annotated[
        list[str] | None,
        typer.Option("--venue", help="Venue name/id to include. Can be repeated."),
    ] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    min_candidate_score: Annotated[
        int, typer.Option("--min-candidate-score", help="Minimum candidate score.")
    ] = 40,
    max_pairs: Annotated[int, typer.Option("--max-pairs", help="Maximum pairs.")] = 10000,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Generates deterministic cross-venue equivalence candidates."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        candidates = EquivalenceService(repo).generate_candidates(
            _parse_datetime(asof) if asof else datetime.now(tz=UTC),
            market_ids=market_ids,
            venue_names=venues,
            min_candidate_score=min_candidate_score,
            max_pairs=max_pairs,
        )

    _print_table(
        headers=("candidate_id", "left_market_id", "right_market_id", "score", "reasons"),
        rows=[
            (
                candidate.candidate_id,
                candidate.left_market_id,
                candidate.right_market_id,
                candidate.candidate_score,
                ",".join(candidate.candidate_reasons),
            )
            for candidate in candidates
        ],
    )


@app.command("equivalence-run")
def equivalence_run_command(
    name: Annotated[str | None, typer.Option("--name", help="Run name.")] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    market_ids: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID to include. Can be repeated."),
    ] = None,
    venues: Annotated[
        list[str] | None,
        typer.Option("--venue", help="Venue name/id to include. Can be repeated."),
    ] = None,
    min_candidate_score: Annotated[
        int, typer.Option("--min-candidate-score", help="Minimum candidate score.")
    ] = 40,
    max_pairs: Annotated[int, typer.Option("--max-pairs", help="Maximum pairs.")] = 10000,
    build_classes: Annotated[
        bool,
        typer.Option("--build-classes/--no-build-classes", help="Build equivalence classes."),
    ] = True,
    force: Annotated[bool, typer.Option("--force", help="Recompute existing hashes.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs a synchronous cross-venue equivalence scan."""

    config = EquivalenceRunConfig(
        name=name,
        asof_timestamp=_parse_datetime(asof) if asof else datetime.now(tz=UTC),
        market_ids=market_ids,
        venue_names=venues,
        min_candidate_score=min_candidate_score,
        max_pairs=max_pairs,
        build_classes=build_classes,
        force=force,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = run_equivalence_scan(config, repo=repo)
        except EquivalenceRunError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "candidates",
            "assessments",
            "classes",
            "comparable_rate",
            "manual_review_rate",
            "do_not_compare_rate",
        ),
        rows=[
            (
                result.run.equivalence_run_id,
                result.summary.total_candidates,
                result.summary.total_assessments,
                result.summary.total_classes,
                result.summary.comparable_rate,
                result.summary.manual_review_rate,
                result.summary.do_not_compare_rate,
            )
        ],
    )


@app.command("equivalence-latest")
def equivalence_latest_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    limit: Annotated[int, typer.Option("--limit", help="Maximum assessments.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints latest stored equivalence assessments involving one market."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        assessments = EquivalenceService(repo).list_equivalence_assessments(
            market_id=market_id,
            limit=limit,
        )

    _print_table(
        headers=("left_market_id", "right_market_id", "status", "permission", "score"),
        rows=[
            (
                assessment.left_market_id,
                assessment.right_market_id,
                assessment.status.value,
                assessment.comparison_permission.value,
                assessment.overall_score,
            )
            for assessment in assessments
        ],
    )


@app.command("equivalence-classes")
def equivalence_classes_command(
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum classes.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints stored equivalence classes."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        classes = EquivalenceService(repo).list_equivalence_classes(
            asof_timestamp=_parse_datetime(asof) if asof else None,
            limit=limit,
        )

    _print_table(
        headers=("class_id", "status", "permission", "market_ids", "min_pair_score"),
        rows=[
            (
                equivalence_class.equivalence_class_id,
                equivalence_class.status.value,
                equivalence_class.comparison_permission.value,
                ",".join(equivalence_class.market_ids),
                equivalence_class.min_pair_score,
            )
            for equivalence_class in classes
        ],
    )


@app.command("divergence-analyze")
def divergence_analyze_command(
    equivalence_assessment_id: Annotated[
        str | None,
        typer.Option(
            "--equivalence-assessment-id",
            help="Equivalence assessment to analyze.",
        ),
    ] = None,
    market_id: Annotated[
        str | None,
        typer.Option("--market-id", help="Analyze assessments involving one market."),
    ] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Recompute existing hashes.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Analyzes cross-venue divergence for an equivalence pair or market."""

    if equivalence_assessment_id is None and market_id is None:
        typer.echo("Provide --equivalence-assessment-id or --market-id.", err=True)
        raise typer.Exit(1)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = DivergenceService(repo)
        try:
            if equivalence_assessment_id is not None:
                analyses = [
                    service.analyze_equivalence_divergence(
                        equivalence_assessment_id,
                        asof_timestamp=_parse_datetime(asof) if asof else None,
                        force=force,
                    )
                ]
            else:
                analyses = service.analyze_market_divergence(
                    market_id or "",
                    asof_timestamp=_parse_datetime(asof) if asof else None,
                    force=force,
                )
        except DivergenceServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "left_market_id",
            "right_market_id",
            "status",
            "score",
            "abs_gap",
            "spread_adjusted_gap",
            "action_hint",
            "reason_codes",
        ),
        rows=[
            (
                analysis.assessment.left_market_id,
                analysis.assessment.right_market_id,
                analysis.assessment.status.value,
                analysis.assessment.overall_divergence_score,
                analysis.assessment.absolute_mid_gap,
                analysis.assessment.spread_adjusted_gap,
                analysis.assessment.action_hint.value,
                ",".join(analysis.assessment.reason_codes),
            )
            for analysis in analyses
        ],
    )


@app.command("divergence-run")
def divergence_run_command(
    name: Annotated[str | None, typer.Option("--name", help="Run name.")] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    equivalence_assessment_ids: Annotated[
        list[str] | None,
        typer.Option(
            "--equivalence-assessment-id",
            help="Equivalence assessment ID. Can be repeated.",
        ),
    ] = None,
    market_ids: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID to include. Can be repeated."),
    ] = None,
    max_pairs: Annotated[int, typer.Option("--max-pairs", help="Maximum pairs.")] = 10000,
    force: Annotated[bool, typer.Option("--force", help="Recompute existing hashes.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs a synchronous cross-venue divergence scan."""

    config = CrossVenueDivergenceRunConfig(
        name=name,
        asof_timestamp=_parse_datetime(asof) if asof else datetime.now(tz=UTC),
        equivalence_assessment_ids=equivalence_assessment_ids,
        market_ids=market_ids,
        max_pairs=max_pairs,
        force=force,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = run_divergence_scan(config, repo=repo)
        except DivergenceRunError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "snapshots",
            "signals",
            "assessments",
            "watch_rate",
            "material_divergence_rate",
            "needs_review_rate",
            "do_not_compare_rate",
        ),
        rows=[
            (
                result.run.divergence_run_id,
                result.summary.total_snapshots,
                result.summary.total_signals,
                result.summary.total_assessments,
                result.summary.watch_rate,
                result.summary.material_divergence_rate,
                result.summary.needs_review_rate,
                result.summary.do_not_compare_rate,
            )
        ],
    )


@app.command("divergence-latest")
def divergence_latest_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints the latest divergence assessment involving one market."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            assessment = DivergenceService(repo).get_latest_market_divergence_assessment(
                market_id,
                _parse_datetime(asof) if asof else None,
            )
        except DivergenceServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=("left_market_id", "right_market_id", "status", "score", "action_hint"),
        rows=[
            (
                assessment.left_market_id,
                assessment.right_market_id,
                assessment.status.value,
                assessment.overall_divergence_score,
                assessment.action_hint.value,
            )
        ],
    )


@app.command("divergence-signals")
def divergence_signals_command(
    market_id: Annotated[
        str | None,
        typer.Option("--market-id", help="Optional market ID filter."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum signals.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints persisted divergence signals."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        signals = DivergenceService(repo).list_divergence_signals(
            market_id=market_id,
            limit=limit,
        )

    _print_table(
        headers=("signal_name", "category", "severity", "score", "action_hint", "reason_code"),
        rows=[
            (
                signal.signal_name,
                signal.category.value,
                signal.severity.value,
                signal.score,
                signal.action_hint.value,
                signal.reason_code,
            )
            for signal in signals
        ],
    )


@app.command("divergence-assessments")
def divergence_assessments_command(
    market_id: Annotated[
        str | None,
        typer.Option("--market-id", help="Optional market ID filter."),
    ] = None,
    status: Annotated[
        DivergenceStatus | None,
        typer.Option("--status", help="Optional divergence status filter."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum assessments.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints persisted divergence assessments."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        assessments = DivergenceService(repo).list_divergence_assessments(
            market_id=market_id,
            status=status,
            limit=limit,
        )

    _print_table(
        headers=("left_market_id", "right_market_id", "status", "score", "action_hint"),
        rows=[
            (
                assessment.left_market_id,
                assessment.right_market_id,
                assessment.status.value,
                assessment.overall_divergence_score,
                assessment.action_hint.value,
            )
            for assessment in assessments
        ],
    )


@app.command("pretrade-check")
def pretrade_check_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    outcome_id: Annotated[
        str | None,
        typer.Option("--outcome-id", help="Optional outcome ID."),
    ] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    side: Annotated[TradeSide, typer.Option("--side", help="Hypothetical side.")] = TradeSide.BUY,
    intent_type: Annotated[
        TradeIntentType,
        typer.Option("--intent-type", help="Hypothetical intent type."),
    ] = TradeIntentType.RESEARCH_ONLY,
    strategy_context: Annotated[
        StrategyContext,
        typer.Option("--strategy-context", help="Strategy context."),
    ] = StrategyContext.RESEARCH,
    requested_price: Annotated[
        str | None,
        typer.Option("--requested-price", help="Optional probability-style price."),
    ] = None,
    requested_size_units: Annotated[
        str,
        typer.Option("--requested-size-units", help="Requested abstract size units."),
    ] = "1",
    policy_id: Annotated[
        str | None,
        typer.Option("--policy-id", help="Optional pre-trade policy ID."),
    ] = None,
    force_recompute_context: Annotated[
        bool,
        typer.Option("--force-recompute-context", help="Recompute dependent context."),
    ] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Evaluates a hypothetical trade intent through the pre-trade gate."""

    asof_timestamp = _parse_datetime(asof) if asof else datetime.now(tz=UTC)
    intent = TradeIntent(
        trade_intent_id="pending",
        market_id=market_id,
        outcome_id=outcome_id,
        venue_id=None,
        strategy_context=strategy_context,
        side=side,
        intent_type=intent_type,
        requested_price=Decimal(requested_price) if requested_price is not None else None,
        requested_size_units=Decimal(requested_size_units),
        requested_notional_usd=None,
        asof_timestamp=asof_timestamp,
        metadata={},
    )
    intent = intent.model_copy(update={"trade_intent_id": compute_trade_intent_id(intent)})
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = PreTradeService(repo).check_pretrade_intent(
                intent,
                policy_id=policy_id,
                force_recompute_context=force_recompute_context,
            )
        except PreTradeServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    decision = result.decision
    _print_table(
        headers=(
            "market_id",
            "action",
            "final_allowed_size_units",
            "composite_risk_score",
            "hard_blockers",
            "warnings",
            "reason_codes",
        ),
        rows=[
            (
                decision.market_id,
                decision.action.value,
                decision.final_allowed_size_units,
                decision.composite_risk_score,
                ",".join(decision.hard_blockers),
                ",".join(decision.warnings),
                ",".join(decision.reason_codes),
            )
        ],
    )


@app.command("pretrade-run")
def pretrade_run_command(
    name: Annotated[str | None, typer.Option("--name", help="Run name.")] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    market_ids: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID to include. Can be repeated."),
    ] = None,
    max_checks: Annotated[int, typer.Option("--max-checks", help="Maximum checks.")] = 10000,
    requested_size_units: Annotated[
        str,
        typer.Option("--requested-size-units", help="Default requested abstract size units."),
    ] = "1",
    strategy_context: Annotated[
        StrategyContext,
        typer.Option("--strategy-context", help="Strategy context."),
    ] = StrategyContext.RESEARCH,
    intent_type: Annotated[
        TradeIntentType,
        typer.Option("--intent-type", help="Default intent type."),
    ] = TradeIntentType.RESEARCH_ONLY,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs default pre-trade checks for selected markets."""

    config = PreTradeRunConfig(
        name=name,
        asof_timestamp=_parse_datetime(asof) if asof else datetime.now(tz=UTC),
        market_ids=market_ids,
        max_checks=max_checks,
        default_requested_size_units=Decimal(requested_size_units),
        strategy_context=strategy_context,
        intent_type=intent_type,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = run_pretrade_checks(config, repo=repo)
        except PreTradeRunError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "total_decisions",
            "no_trade_rate",
            "manual_review_rate",
            "passive_only_rate",
            "allow_smaller_size_rate",
            "allow_rate",
            "hard_block_rate",
        ),
        rows=[
            (
                result.run.pretrade_run_id,
                result.summary.total_decisions,
                result.summary.no_trade_rate,
                result.summary.manual_review_rate,
                result.summary.passive_only_rate,
                result.summary.allow_smaller_size_rate,
                result.summary.allow_rate,
                result.summary.hard_block_rate,
            )
        ],
    )


@app.command("pretrade-latest")
def pretrade_latest_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints the latest persisted pre-trade decision for a market."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            decision = PreTradeService(repo).get_latest_pretrade_decision_asof(
                market_id,
                _parse_datetime(asof) if asof else datetime.now(tz=UTC),
            )
        except PreTradeServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=("market_id", "action", "final_allowed_size_units", "risk", "reason_codes"),
        rows=[
            (
                decision.market_id,
                decision.action.value,
                decision.final_allowed_size_units,
                decision.composite_risk_score,
                ",".join(decision.reason_codes),
            )
        ],
    )


@app.command("pretrade-decisions")
def pretrade_decisions_command(
    market_id: Annotated[
        str | None,
        typer.Option("--market-id", help="Optional market ID filter."),
    ] = None,
    action: Annotated[
        PreTradeAction | None,
        typer.Option("--action", help="Optional action filter."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum decisions.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints persisted pre-trade decisions."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        decisions = PreTradeService(repo).list_pretrade_decisions(
            market_id=market_id,
            action=action,
            limit=limit,
        )

    _print_table(
        headers=("asof_timestamp", "market_id", "action", "final_size", "risk"),
        rows=[
            (
                decision.asof_timestamp.isoformat(),
                decision.market_id,
                decision.action.value,
                decision.final_allowed_size_units,
                decision.composite_risk_score,
            )
            for decision in decisions
        ],
    )


@app.command("pretrade-create-default-policy")
def pretrade_create_default_policy_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Creates the deterministic default pre-trade policy if missing."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        policy = PreTradeService(repo).create_default_pretrade_policy_if_missing()

    _print_table(
        headers=("policy_id", "policy_name", "policy_version", "is_active"),
        rows=[(policy.policy_id, policy.policy_name, policy.policy_version, policy.is_active)],
    )


@app.command("pretrade-restrictions")
def pretrade_restrictions_command(
    limit: Annotated[int, typer.Option("--limit", help="Maximum restrictions.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints configured pre-trade restriction rules."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        rules = PreTradeService(repo).list_market_restriction_rules(limit=limit)

    _print_table(
        headers=("restriction_id", "type", "scope", "market_id", "reason_code"),
        rows=[
            (
                rule.restriction_id,
                rule.restriction_type.value,
                rule.scope_type.value,
                rule.market_id or "",
                rule.reason_code,
            )
            for rule in rules
        ],
    )


@app.command("pretrade-add-restriction")
def pretrade_add_restriction_command(
    restriction_type: Annotated[
        RestrictionType,
        typer.Option("--restriction-type", help="Restriction type."),
    ],
    scope_type: Annotated[
        RestrictionScopeType,
        typer.Option("--scope-type", help="Restriction scope type."),
    ],
    reason_code: Annotated[str, typer.Option("--reason-code", help="Reason code.")],
    venue_id: Annotated[str | None, typer.Option("--venue-id", help="Venue ID.")] = None,
    venue_name: Annotated[
        str | None, typer.Option("--venue-name", help="Venue name.")
    ] = None,
    market_id: Annotated[
        str | None, typer.Option("--market-id", help="Market ID.")
    ] = None,
    event_id: Annotated[str | None, typer.Option("--event-id", help="Event ID.")] = None,
    category: Annotated[str | None, typer.Option("--category", help="Category.")] = None,
    title_pattern: Annotated[
        str | None,
        typer.Option("--title-pattern", help="Title substring pattern."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="Description."),
    ] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Adds a pre-trade restriction rule."""

    payload = MarketRestrictionRuleCreate(
        restriction_type=restriction_type,
        scope_type=scope_type,
        venue_id=venue_id,
        venue_name=venue_name,
        market_id=market_id,
        event_id=event_id,
        category=category,
        title_pattern=title_pattern,
        reason_code=reason_code,
        description=description,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        rule = PreTradeService(repo).save_market_restriction_rule(payload)

    _print_table(
        headers=("restriction_id", "type", "scope", "reason_code"),
        rows=[
            (
                rule.restriction_id,
                rule.restriction_type.value,
                rule.scope_type.value,
                rule.reason_code,
            )
        ],
    )


@app.command("pretrade-add-exposure")
def pretrade_add_exposure_command(
    market_id: Annotated[
        str | None,
        typer.Option("--market-id", help="Optional market ID."),
    ] = None,
    event_id: Annotated[str | None, typer.Option("--event-id", help="Optional event ID.")] = None,
    venue_id: Annotated[str | None, typer.Option("--venue-id", help="Optional venue ID.")] = None,
    strategy_context: Annotated[
        str | None,
        typer.Option("--strategy-context", help="Optional strategy context."),
    ] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="Optional ISO as-of time.")] = None,
    market_exposure_units: Annotated[
        str,
        typer.Option("--market-exposure-units", help="Market exposure units."),
    ] = "0",
    event_exposure_units: Annotated[
        str,
        typer.Option("--event-exposure-units", help="Event exposure units."),
    ] = "0",
    venue_exposure_units: Annotated[
        str,
        typer.Option("--venue-exposure-units", help="Venue exposure units."),
    ] = "0",
    strategy_exposure_units: Annotated[
        str | None,
        typer.Option("--strategy-exposure-units", help="Strategy exposure units."),
    ] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Adds an abstract exposure snapshot for policy testing."""

    payload = ExposureSnapshotCreate(
        asof_timestamp=_parse_datetime(asof) if asof else None,
        source=ExposureSource.MANUAL,
        market_id=market_id,
        event_id=event_id,
        venue_id=venue_id,
        strategy_context=strategy_context,
        market_exposure_units=Decimal(market_exposure_units),
        event_exposure_units=Decimal(event_exposure_units),
        venue_exposure_units=Decimal(venue_exposure_units),
        strategy_exposure_units=(
            Decimal(strategy_exposure_units)
            if strategy_exposure_units is not None
            else None
        ),
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        snapshot = PreTradeService(repo).save_exposure_snapshot(payload)

    _print_table(
        headers=("exposure_snapshot_id", "asof_timestamp", "market", "event", "venue"),
        rows=[
            (
                snapshot.exposure_snapshot_id,
                snapshot.asof_timestamp.isoformat(),
                snapshot.market_exposure_units,
                snapshot.event_exposure_units,
                snapshot.venue_exposure_units,
            )
        ],
    )


@app.command("paper-create-default-policy")
def paper_create_default_policy_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Creates the deterministic default simulated paper policy if missing."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        policy = PaperExecutionService(repo).create_default_paper_execution_policy_if_missing()

    _print_table(
        headers=("paper_policy_id", "policy_name", "policy_version", "fill_model"),
        rows=[
            (
                policy.paper_policy_id,
                policy.policy_name,
                policy.policy_version,
                policy.fill_model.value,
            )
        ],
    )


@app.command("paper-simulate-intent")
def paper_simulate_intent_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    outcome_id: Annotated[str | None, typer.Option("--outcome-id")] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="ISO as-of time.")] = None,
    side: Annotated[TradeSide, typer.Option("--side", help="BUY or SELL.")] = TradeSide.BUY,
    intent_type: Annotated[
        TradeIntentType,
        typer.Option("--intent-type", help="Intent type."),
    ] = TradeIntentType.RESEARCH_ONLY,
    strategy_context: Annotated[
        StrategyContext,
        typer.Option("--strategy-context", help="Strategy context."),
    ] = StrategyContext.RESEARCH,
    requested_price: Annotated[
        str | None,
        typer.Option("--requested-price", help="Optional probability price."),
    ] = None,
    requested_size_units: Annotated[
        str,
        typer.Option("--requested-size-units", help="Requested simulated units."),
    ] = "1",
    paper_policy_id: Annotated[
        str | None,
        typer.Option("--paper-policy-id", help="Paper policy ID."),
    ] = None,
    force_recompute_pretrade: Annotated[
        bool,
        typer.Option("--force-recompute-pretrade", help="Recompute pretrade context."),
    ] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Simulates one hypothetical paper intent after pre-trade approval."""

    asof_timestamp = _parse_datetime(asof) if asof else datetime.now(tz=UTC)
    request = PaperSimulateIntentRequest(
        market_id=market_id,
        outcome_id=outcome_id,
        strategy_context=strategy_context,
        side=side,
        intent_type=intent_type,
        requested_price=Decimal(requested_price) if requested_price is not None else None,
        requested_size_units=Decimal(requested_size_units),
        asof_timestamp=asof_timestamp,
        paper_policy_id=paper_policy_id,
        force_recompute_pretrade=force_recompute_pretrade,
    )
    intent = compute_trade_intent_from_request(request, asof_timestamp)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = PaperExecutionService(repo).simulate_trade_intent(
                intent,
                paper_policy_id=paper_policy_id,
                force_recompute_pretrade=force_recompute_pretrade,
            )
        except PaperServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    filled_size = sum((fill.size_units for fill in result.fills), Decimal("0"))
    notional = sum((fill.notional for fill in result.fills), Decimal("0"))
    avg_fill_price = notional / filled_size if filled_size > Decimal("0") else ""
    _print_table(
        headers=(
            "market_id",
            "order_status",
            "fills",
            "filled_size",
            "avg_fill_price",
            "final_position",
            "portfolio_equity_simulated",
            "reason_codes",
        ),
        rows=[
            (
                result.order.market_id,
                result.order.status.value,
                len(result.fills),
                filled_size,
                avg_fill_price,
                (
                    result.position_snapshot.position_units
                    if result.position_snapshot
                    else ""
                ),
                (
                    result.portfolio_snapshot.total_equity_simulated
                    if result.portfolio_snapshot
                    else ""
                ),
                ",".join(result.order.rejection_reason_codes),
            )
        ],
    )


@app.command("paper-orders")
def paper_orders_command(
    market_id: Annotated[str | None, typer.Option("--market-id")] = None,
    status_filter: Annotated[
        PaperOrderStatus | None,
        typer.Option("--status", help="Optional paper order status."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum rows.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints simulated paper orders."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        orders = PaperExecutionService(repo).list_paper_orders(
            market_id=market_id,
            status=status_filter,
            limit=limit,
        )

    _print_table(
        headers=("paper_order_id", "market_id", "status", "accepted", "filled"),
        rows=[
            (
                order.paper_order_id,
                order.market_id,
                order.status.value,
                order.accepted_size_units,
                order.filled_size_units,
            )
            for order in orders
        ],
    )


@app.command("paper-fills")
def paper_fills_command(
    market_id: Annotated[str | None, typer.Option("--market-id")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum rows.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints simulated paper fills."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        fills = PaperExecutionService(repo).list_paper_fills(market_id=market_id, limit=limit)

    _print_table(
        headers=("paper_fill_id", "market_id", "side", "price", "size", "fee_simulated"),
        rows=[
            (
                fill.paper_fill_id,
                fill.market_id,
                fill.side.value,
                fill.price,
                fill.size_units,
                fill.fee_amount,
            )
            for fill in fills
        ],
    )


@app.command("paper-position-latest")
def paper_position_latest_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="ISO as-of time.")] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints the latest simulated position snapshot."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            snapshot = PaperExecutionService(repo).get_latest_paper_position_asof(
                market_id,
                asof_timestamp=_parse_datetime(asof) if asof else datetime.now(tz=UTC),
            )
        except PaperServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=("market_id", "position_units", "avg_entry", "unrealized_simulated"),
        rows=[
            (
                snapshot.market_id,
                snapshot.position_units,
                snapshot.average_entry_price or "",
                snapshot.unrealized_pnl_simulated,
            )
        ],
    )


@app.command("paper-portfolio-latest")
def paper_portfolio_latest_command(
    simulation_run_id: Annotated[
        str | None,
        typer.Option("--simulation-run-id", help="Optional simulation run ID."),
    ] = None,
    asof: Annotated[str | None, typer.Option("--asof", help="ISO as-of time.")] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints the latest simulated portfolio snapshot."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        try:
            snapshot = PaperExecutionService(repo).get_latest_paper_portfolio_asof(
                simulation_run_id=simulation_run_id,
                asof_timestamp=_parse_datetime(asof) if asof else datetime.now(tz=UTC),
            )
        except PaperServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=("cash_simulated", "equity_simulated", "gross_exposure_simulated"),
        rows=[
            (
                snapshot.cash_balance_simulated,
                snapshot.total_equity_simulated,
                snapshot.gross_exposure_simulated,
            )
        ],
    )


@app.command("paper-run")
def paper_run_command(
    start: Annotated[str, typer.Option("--start", help="Start ISO datetime.")],
    end: Annotated[str, typer.Option("--end", help="End ISO datetime.")],
    name: Annotated[str | None, typer.Option("--name")] = None,
    interval_seconds: Annotated[
        int,
        typer.Option("--interval-seconds", help="Interval seconds."),
    ] = 3600,
    market_id: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID. Repeatable."),
    ] = None,
    max_orders: Annotated[int, typer.Option("--max-orders")] = 10000,
    initial_cash_simulated: Annotated[
        str,
        typer.Option("--initial-cash-simulated"),
    ] = "1000",
    paper_policy_id: Annotated[str | None, typer.Option("--paper-policy-id")] = None,
    default_order_size_units: Annotated[
        str,
        typer.Option("--default-order-size-units"),
    ] = "1",
    default_intent_type: Annotated[
        TradeIntentType,
        typer.Option("--default-intent-type"),
    ] = TradeIntentType.RESEARCH_ONLY,
    default_strategy_context: Annotated[
        StrategyContext,
        typer.Option("--default-strategy-context"),
    ] = StrategyContext.RESEARCH,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs a synchronous simulated paper execution batch."""

    config = PaperSimulationRunConfig(
        name=name,
        start_time=_parse_datetime(start),
        end_time=_parse_datetime(end),
        interval_seconds=interval_seconds,
        market_ids=list(market_id or []) or None,
        max_orders=max_orders,
        initial_cash_simulated=Decimal(initial_cash_simulated),
        paper_policy_id=paper_policy_id,
        default_order_size_units=Decimal(default_order_size_units),
        default_intent_type=default_intent_type,
        default_strategy_context=default_strategy_context,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            result = run_paper_simulation(config, repo=repo)
        except PaperRunError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc

    _print_table(
        headers=(
            "run_id",
            "total_orders",
            "filled_orders",
            "rejected_orders",
            "total_fills",
            "final_equity_simulated",
            "fill_rate",
            "rejection_rate",
        ),
        rows=[
            (
                result.run.simulation_run_id,
                result.summary.total_orders,
                result.summary.filled_orders,
                result.summary.rejected_orders,
                result.summary.total_fills,
                result.summary.final_total_equity_simulated,
                result.summary.fill_rate,
                result.summary.rejection_rate,
            )
        ],
    )


@app.command("research-create-default-strategies")
def research_create_default_strategies_command(
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Creates deterministic default research strategies if missing."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        strategies = ResearchService(repo).create_default_research_strategies_if_missing()
    _print_table(
        headers=("strategy_id", "strategy_name", "family", "active"),
        rows=[
            (
                strategy.strategy_id,
                strategy.strategy_name,
                strategy.family.value,
                strategy.is_active,
            )
            for strategy in strategies
        ],
    )


@app.command("research-strategies")
def research_strategies_command(
    limit: Annotated[int, typer.Option("--limit", help="Rows to print.")] = 50,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Lists research strategy definitions."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        strategies = ResearchService(PredictionMarketRepository(session)).list_research_strategies(
            limit=limit
        )
    _print_table(
        headers=("strategy_id", "strategy_name", "version", "family"),
        rows=[
            (
                strategy.strategy_id,
                strategy.strategy_name,
                strategy.strategy_version,
                strategy.family.value,
            )
            for strategy in strategies
        ],
    )


@app.command("research-build-features")
def research_build_features_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="ISO as-of time.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Force duplicate rebuild.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Builds generic as-of research features."""

    asof_timestamp = _parse_datetime(asof) if asof else datetime.now(tz=UTC)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        features = ResearchService(PredictionMarketRepository(session)).build_features_for_market(
            market_id,
            asof_timestamp,
            force=force,
        )
    _print_table(
        headers=("market_id", "source", "family", "reason_codes"),
        rows=[
            (
                feature.market_id,
                feature.feature_source.value,
                feature.feature_family.value,
                ",".join(feature.reason_codes),
            )
            for feature in features
        ],
    )


@app.command("research-generate-signals")
def research_generate_signals_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="ISO as-of time.")] = None,
    strategy_id: Annotated[
        list[str] | None,
        typer.Option("--strategy-id", help="Strategy ID; repeatable."),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Force duplicate generation.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Generates deterministic research signals."""

    asof_timestamp = _parse_datetime(asof) if asof else datetime.now(tz=UTC)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        signals = ResearchService(PredictionMarketRepository(session)).generate_research_signals(
            market_id,
            asof_timestamp,
            strategy_ids=list(strategy_id or []) or None,
            force=force,
        )
    _print_table(
        headers=(
            "market_id",
            "strategy",
            "signal_type",
            "action_bias",
            "signal_strength_score",
            "confidence_score",
            "reason_codes",
        ),
        rows=[
            (
                signal.market_id,
                signal.strategy_name,
                signal.signal_type.value,
                signal.action_bias.value,
                signal.signal_strength_score,
                signal.confidence_score,
                ",".join(signal.reason_codes),
            )
            for signal in signals
        ],
    )


@app.command("research-generate-proposals")
def research_generate_proposals_command(
    market_id: Annotated[str, typer.Option("--market-id", help="Market ID.")],
    asof: Annotated[str | None, typer.Option("--asof", help="ISO as-of time.")] = None,
    strategy_id: Annotated[
        list[str] | None,
        typer.Option("--strategy-id", help="Strategy ID; repeatable."),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Force duplicate generation.")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Generates hypothetical research intent proposals."""

    asof_timestamp = _parse_datetime(asof) if asof else datetime.now(tz=UTC)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        proposals = ResearchService(
            PredictionMarketRepository(session)
        ).generate_research_proposals(
            market_id,
            asof_timestamp,
            strategy_ids=list(strategy_id or []) or None,
            force=force,
        )
    _print_table(
        headers=(
            "proposal_id",
            "market_id",
            "strategy",
            "side",
            "intent_type",
            "requested_size_units",
            "reason_codes",
        ),
        rows=[
            (
                proposal.proposal_id,
                proposal.market_id,
                proposal.strategy_name,
                proposal.side.value,
                proposal.intent_type,
                proposal.requested_size_units,
                ",".join(proposal.reason_codes),
            )
            for proposal in proposals
        ],
    )


@app.command("research-evaluate-proposal")
def research_evaluate_proposal_command(
    proposal_id: Annotated[str, typer.Option("--proposal-id", help="Proposal ID.")],
    paper_simulation: Annotated[
        bool,
        typer.Option("--paper-simulation/--no-paper-simulation"),
    ] = True,
    paper_policy_id: Annotated[
        str | None,
        typer.Option("--paper-policy-id", help="Paper policy ID."),
    ] = None,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Evaluates one research proposal through pre-trade and optional paper simulation."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        try:
            trace = ResearchService(
                PredictionMarketRepository(session)
            ).evaluate_research_proposal(
                proposal_id,
                enable_paper_simulation=paper_simulation,
                paper_policy_id=paper_policy_id,
            )
        except ResearchServiceError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc
    _print_table(
        headers=(
            "proposal_id",
            "pretrade_action",
            "paper_order_status",
            "filled_size_simulated",
            "reason_codes",
        ),
        rows=[
            (
                trace.proposal_id,
                trace.pretrade_action,
                trace.paper_order_status,
                trace.filled_size_units_simulated,
                ",".join(trace.reason_codes),
            )
        ],
    )


@app.command("research-run")
def research_run_command(
    start: Annotated[str, typer.Option("--start", help="Start ISO timestamp.")],
    end: Annotated[str, typer.Option("--end", help="End ISO timestamp.")],
    name: Annotated[str | None, typer.Option("--name", help="Run name.")] = None,
    interval_seconds: Annotated[
        int,
        typer.Option("--interval-seconds", help="Step interval."),
    ] = 3600,
    strategy_id: Annotated[
        list[str] | None,
        typer.Option("--strategy-id", help="Strategy ID; repeatable."),
    ] = None,
    market_id: Annotated[
        list[str] | None,
        typer.Option("--market-id", help="Market ID; repeatable."),
    ] = None,
    max_steps: Annotated[int, typer.Option("--max-steps")] = 10000,
    max_proposals: Annotated[int, typer.Option("--max-proposals")] = 10000,
    paper_simulation: Annotated[
        bool,
        typer.Option("--paper-simulation/--no-paper-simulation"),
    ] = True,
    paper_policy_id: Annotated[
        str | None,
        typer.Option("--paper-policy-id", help="Paper policy ID."),
    ] = None,
    initial_cash_simulated: Annotated[
        str,
        typer.Option("--initial-cash-simulated", help="Initial simulated cash."),
    ] = "1000",
    force: Annotated[bool, typer.Option("--force")] = False,
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read/write.")
    ] = None,
) -> None:
    """Runs a deterministic strategy research simulation."""

    config = ResearchRunConfig(
        name=name,
        start_time=_parse_datetime(start),
        end_time=_parse_datetime(end),
        interval_seconds=interval_seconds,
        strategy_ids=list(strategy_id or []) or None,
        market_ids=list(market_id or []) or None,
        max_steps=max_steps,
        max_proposals=max_proposals,
        enable_paper_simulation=paper_simulation,
        paper_policy_id=paper_policy_id,
        initial_cash_simulated=Decimal(initial_cash_simulated),
        force=force,
    )
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        try:
            result = run_research_simulation(
                config,
                repo=PredictionMarketRepository(session),
            )
        except ResearchRunError as exc:
            typer.echo(exc.code, err=True)
            raise typer.Exit(1) from exc
    _print_table(
        headers=(
            "run_id",
            "signals",
            "proposals",
            "pretrade_checks",
            "paper_orders",
            "paper_fills",
            "proposal_pass_rate",
            "paper_fill_rate",
        ),
        rows=[
            (
                result.run.research_run_id,
                result.summary.total_signals,
                result.summary.total_proposals,
                result.summary.total_pretrade_checks,
                result.summary.total_paper_orders,
                result.summary.total_paper_fills,
                result.summary.proposal_to_pretrade_pass_rate,
                result.summary.paper_fill_rate,
            )
        ],
    )


@app.command("research-summary")
def research_summary_command(
    run_id: Annotated[str, typer.Option("--run-id", help="Research run ID.")],
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints a stored research run summary."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        summary = ResearchService(
            PredictionMarketRepository(session)
        ).get_research_run_summary(run_id)
    _print_table(
        headers=(
            "run_id",
            "signals",
            "proposals",
            "pretrade_checks",
            "paper_orders",
            "paper_fills",
        ),
        rows=[
            (
                summary.research_run_id,
                summary.total_signals,
                summary.total_proposals,
                summary.total_pretrade_checks,
                summary.total_paper_orders,
                summary.total_paper_fills,
            )
        ],
    )


@app.command("research-attribution")
def research_attribution_command(
    run_id: Annotated[str, typer.Option("--run-id", help="Research run ID.")],
    database_url: Annotated[
        str | None, typer.Option("--database-url", help="Database URL to read.")
    ] = None,
) -> None:
    """Prints a compact research attribution report."""

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        report = ResearchService(
            PredictionMarketRepository(session)
        ).get_research_attribution_report(run_id)
    _print_table(
        headers=("run_id", "strategies", "markets", "pretrade_actions", "paper_statuses"),
        rows=[
            (
                report.research_run_id,
                report.by_strategy,
                report.by_market,
                report.by_pretrade_action,
                report.by_paper_order_status,
            )
        ],
    )


def _print_table(headers: tuple[str, ...], rows: Sequence[Sequence[object]]) -> None:
    normalized_rows = [tuple(str(value) for value in row) for row in rows]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in normalized_rows))
        for index in range(len(headers))
    ]
    typer.echo(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    typer.echo("-+-".join("-" * width for width in widths))
    for row in normalized_rows:
        typer.echo(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _ingestion_run_row(run: IngestionRun) -> tuple[str, str, str, int, int, int, int, int]:
    return (
        run.ingestion_run_id,
        run.venue_name,
        run.status.value,
        run.payloads_archived,
        run.markets_created,
        run.rule_snapshots_created,
        run.orderbook_snapshots_created,
        run.errors_count,
    )


if __name__ == "__main__":
    app()
