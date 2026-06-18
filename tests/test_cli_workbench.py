from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app
from tests.paper_helpers import MARKET_ID


def test_cli_workbench_queue_card_and_notes_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_workbench.db'}"
    runner = CliRunner()

    assert runner.invoke(app, ["init-db", "--database-url", database_url]).exit_code == 0
    assert (
        runner.invoke(app, ["load-sample-data", "--database-url", database_url]).exit_code
        == 0
    )
    queue = runner.invoke(
        app,
        [
            "workbench-build-queue",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    card = runner.invoke(
        app,
        [
            "workbench-card",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    latest_queue = runner.invoke(
        app,
        [
            "workbench-queue",
            "--database-url",
            database_url,
            "--latest",
        ],
    )
    queue_summary = runner.invoke(
        app,
        [
            "workbench-queue-summary",
            "--database-url",
            database_url,
        ],
    )
    note = runner.invoke(
        app,
        [
            "workbench-add-note",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--text",
            "CLI desk note.",
        ],
    )
    notes = runner.invoke(
        app,
        ["workbench-notes", "--database-url", database_url, "--market-id", MARKET_ID],
    )
    run = runner.invoke(
        app,
        [
            "workbench-run",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )

    assert queue.exit_code == 0
    assert MARKET_ID in queue.output
    assert latest_queue.exit_code == 0
    assert "review_action" in latest_queue.output
    assert queue_summary.exit_code == 0
    assert "priority_bucket_counts" in queue_summary.output
    assert card.exit_code == 0
    assert "review_action" in card.output
    assert note.exit_code == 0
    assert "desk_note_" in note.output
    assert notes.exit_code == 0
    assert "CLI desk note." in notes.output
    assert run.exit_code == 0
    assert "workbench_run_" in run.output
