from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from prediction_desk.persistence.database import init_db
from tests.api_test_helpers import build_test_client, sqlite_url

SAMPLE_DIR = Path("sample_data/vendor_samples")


def test_api_vendor_source_sample_and_evaluate_work(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    database_url = sqlite_url(tmp_path / "api_vendor_data.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    source = client.post(
        "/api/v1/vendor-data/sources",
        json={
            "vendor_name": "SampleVendor",
            "dataset_name": "Polymarket history",
            "dataset_version": "sample-v1",
            "license_status": "SAMPLE_ONLY",
        },
    )
    vendor_source_id = source.json()["vendor_source_id"]
    sample = client.post(
        "/api/v1/vendor-data/samples/load",
        json={
            "vendor_source_id": vendor_source_id,
            "file_path": str(SAMPLE_DIR / "polymarket_price_history_sample.csv"),
        },
    )
    sample_file_id = sample.json()["sample_file_id"]
    inspection = client.post(f"/api/v1/vendor-data/samples/{sample_file_id}/inspect")
    validation = client.post(f"/api/v1/vendor-data/samples/{sample_file_id}/validate")
    dry_run = client.post(
        f"/api/v1/vendor-data/samples/{sample_file_id}/dry-run-import",
        json={"sample_kind": "price_history"},
    )
    dry_run_default = client.post(
        f"/api/v1/vendor-data/samples/{sample_file_id}/dry-run-import",
    )
    evaluation = client.post(
        "/api/v1/vendor-data/evaluate",
        json={"vendor_source_id": vendor_source_id, "sample_file_ids": [sample_file_id]},
    )

    assert source.status_code == 200
    assert sample.status_code == 200
    assert inspection.status_code == 200
    assert "token_id" in inspection.json()["token_identifier_columns"]
    assert validation.status_code == 200
    assert dry_run.status_code == 200
    assert dry_run.json()["canonical_price_snapshots_detected"] == 3
    assert dry_run_default.status_code == 200
    assert evaluation.status_code == 200
    assert evaluation.json()["evaluation_report_id"].startswith("vendor_eval_")


def test_api_vendor_load_rejects_url(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    database_url = sqlite_url(tmp_path / "api_vendor_url.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)
    source = client.post(
        "/api/v1/vendor-data/sources",
        json={
            "vendor_name": "SampleVendor",
            "dataset_name": "Bad URL",
            "dataset_version": "sample-v1",
        },
    )

    response = client.post(
        "/api/v1/vendor-data/samples/load",
        json={
            "vendor_source_id": source.json()["vendor_source_id"],
            "file_path": "https://example.com/data.csv",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "vendor_file_path_must_be_local"
