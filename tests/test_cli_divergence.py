from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app
from tests.equivalence_helpers import KALSHI_RAIN, POLYMARKET_RAIN
from tests.test_divergence_service import DIVERGENCE_ASOF


def test_cli_divergence_analyze_run_latest_signals_and_assessments_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_divergence.db'}"
    runner = CliRunner()

    assert runner.invoke(
        app,
        ["ingestion-run-once", "--database-url", database_url, "--venue", "kalshi"],
    ).exit_code == 0
    assert runner.invoke(
        app,
        ["ingestion-run-once", "--database-url", database_url, "--venue", "polymarket"],
    ).exit_code == 0
    assess_result = runner.invoke(
        app,
        [
            "equivalence-assess",
            "--database-url",
            database_url,
            "--left-market-id",
            KALSHI_RAIN,
            "--right-market-id",
            POLYMARKET_RAIN,
            "--asof",
            DIVERGENCE_ASOF.isoformat(),
        ],
    )
    assert assess_result.exit_code == 0

    analyze_result = runner.invoke(
        app,
        [
            "divergence-analyze",
            "--database-url",
            database_url,
            "--market-id",
            KALSHI_RAIN,
            "--asof",
            DIVERGENCE_ASOF.isoformat(),
        ],
    )
    run_result = runner.invoke(
        app,
        [
            "divergence-run",
            "--database-url",
            database_url,
            "--market-id",
            KALSHI_RAIN,
            "--asof",
            DIVERGENCE_ASOF.isoformat(),
            "--max-pairs",
            "10",
        ],
    )
    latest_result = runner.invoke(
        app,
        ["divergence-latest", "--database-url", database_url, "--market-id", KALSHI_RAIN],
    )
    signals_result = runner.invoke(
        app,
        ["divergence-signals", "--database-url", database_url],
    )
    assessments_result = runner.invoke(
        app,
        ["divergence-assessments", "--database-url", database_url],
    )

    assert analyze_result.exit_code == 0
    assert "MATERIAL_DIVERGENCE" in analyze_result.output
    assert run_result.exit_code == 0
    assert "material_divergence_rate" in run_result.output
    assert latest_result.exit_code == 0
    assert "action_hint" in latest_result.output
    assert signals_result.exit_code == 0
    assert "EQUIVALENT_PRICE_GAP" in signals_result.output
    assert assessments_result.exit_code == 0
    assert "MATERIAL_DIVERGENCE" in assessments_result.output


def test_cli_divergence_analyze_requires_assessment_or_market(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_divergence_bad.db'}"
    runner = CliRunner()

    result = runner.invoke(app, ["divergence-analyze", "--database-url", database_url])

    assert result.exit_code == 1
    assert "Provide --equivalence-assessment-id or --market-id" in result.output
