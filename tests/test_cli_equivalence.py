from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app
from tests.equivalence_helpers import ASOF, KALSHI_RAIN, POLYMARKET_RAIN


def test_cli_equivalence_assess_candidates_and_classes_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_equivalence.db'}"
    runner = CliRunner()

    assert runner.invoke(
        app,
        ["ingestion-run-once", "--database-url", database_url, "--venue", "kalshi"],
    ).exit_code == 0
    assert runner.invoke(
        app,
        ["ingestion-run-once", "--database-url", database_url, "--venue", "polymarket"],
    ).exit_code == 0

    candidates_result = runner.invoke(
        app,
        [
            "equivalence-candidates",
            "--database-url",
            database_url,
            "--market-id",
            KALSHI_RAIN,
            "--market-id",
            POLYMARKET_RAIN,
            "--asof",
            ASOF.isoformat(),
        ],
    )
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
            ASOF.isoformat(),
        ],
    )
    run_result = runner.invoke(
        app,
        [
            "equivalence-run",
            "--database-url",
            database_url,
            "--market-id",
            KALSHI_RAIN,
            "--market-id",
            POLYMARKET_RAIN,
            "--asof",
            ASOF.isoformat(),
            "--max-pairs",
            "10",
        ],
    )
    latest_result = runner.invoke(
        app,
        [
            "equivalence-latest",
            "--database-url",
            database_url,
            "--market-id",
            KALSHI_RAIN,
        ],
    )
    classes_result = runner.invoke(
        app,
        ["equivalence-classes", "--database-url", database_url],
    )

    assert candidates_result.exit_code == 0
    assert "candidate_id" in candidates_result.output
    assert assess_result.exit_code == 0
    assert "overall_score" in assess_result.output
    assert run_result.exit_code == 0
    assert re.search(r"equivalence_run_[a-f0-9]{24}", run_result.output)
    assert latest_result.exit_code == 0
    assert "permission" in latest_result.output
    assert classes_result.exit_code == 0
    assert "class_id" in classes_result.output
