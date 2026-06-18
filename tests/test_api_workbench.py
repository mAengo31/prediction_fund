from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url
from tests.paper_helpers import MARKET_ID


def test_api_workbench_queue_card_and_notes_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = sqlite_url(tmp_path / "api_workbench.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    queue = client.post(
        "/api/v1/workbench/queues/build",
        json={
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "market_ids": [MARKET_ID],
        },
    )
    latest_queue = client.get("/api/v1/workbench/queues/latest")
    queue_summary = client.get("/api/v1/workbench/queues/summary")
    card = client.post(
        f"/api/v1/workbench/markets/{MARKET_ID}/decision-card",
        json={"asof_timestamp": "2026-06-16T12:00:00Z"},
    )
    latest = client.get(f"/api/v1/workbench/markets/{MARKET_ID}/decision-card/latest")
    note = client.post(
        "/api/v1/workbench/notes",
        json={"market_id": MARKET_ID, "text": "Desk review note."},
    )
    notes = client.get("/api/v1/workbench/notes", params={"market_id": MARKET_ID})
    run = client.post(
        "/api/v1/workbench/runs",
        json={
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "market_ids": [MARKET_ID],
        },
    )

    assert queue.status_code == 200
    assert queue.json()[0]["market_id"] == MARKET_ID
    assert latest_queue.status_code == 200
    assert latest_queue.json()[0]["market_id"] == MARKET_ID
    assert queue_summary.status_code == 200
    assert queue_summary.json()["total_items"] == 1
    assert card.status_code == 200
    assert card.json()["market_id"] == MARKET_ID
    assert latest.status_code == 200
    assert note.status_code == 200
    assert notes.status_code == 200
    assert notes.json()[0]["note_id"] == note.json()["note_id"]
    assert run.status_code == 200
    assert run.json()["summary"]["total_queue_items"] == 1
