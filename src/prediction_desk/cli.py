"""Command-line interface for local research workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import typer

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scoring.trust_verdict import build_trust_verdict

app = typer.Typer(no_args_is_help=True)


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


def _print_table(headers: tuple[str, ...], rows: list[tuple[str, str, int, int, str, str]]) -> None:
    normalized_rows = [tuple(str(value) for value in row) for row in rows]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in normalized_rows))
        for index in range(len(headers))
    ]
    typer.echo(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    typer.echo("-+-".join("-" * width for width in widths))
    for row in normalized_rows:
        typer.echo(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


if __name__ == "__main__":
    app()
