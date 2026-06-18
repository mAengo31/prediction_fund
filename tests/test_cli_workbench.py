from __future__ import annotations

import re
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
    status = runner.invoke(
        app,
        [
            "workbench-status",
            "--database-url",
            database_url,
        ],
    )
    queue_item_match = re.search(r"queue_item_[0-9a-f]+", latest_queue.output)
    assert queue_item_match is not None
    status_update = runner.invoke(
        app,
        [
            "workbench-update-item-status",
            "--database-url",
            database_url,
            "--queue-item-id",
            queue_item_match.group(0),
            "--review-status",
            "WATCHING",
            "--reviewed-by",
            "cli-test",
            "--review-outcome",
            "NEEDS_MORE_DATA",
            "--review-reason",
            "CLI review status update.",
            "--note-text",
            "CLI linked review note. No trading action.",
            "--tag",
            "cli",
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
    assert status.exit_code == 0
    assert "public_read_schedule_status" in status.output
    assert status_update.exit_code == 0
    assert "WATCHING" in status_update.output
    assert "NEEDS_MORE_DATA" in status_update.output
    assert card.exit_code == 0
    assert "review_action" in card.output
    assert note.exit_code == 0
    assert "desk_note_" in note.output
    assert notes.exit_code == 0
    assert "CLI desk note." in notes.output
    assert run.exit_code == 0
    assert "workbench_run_" in run.output
