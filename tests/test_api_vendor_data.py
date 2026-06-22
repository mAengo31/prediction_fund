from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from prediction_desk.persistence.database import init_db
from tests.api_test_helpers import build_test_client, sqlite_url

SAMPLE_DIR = Path("sample_data/vendor_samples")
BTC_MAPPING_CONFIG = (
    SAMPLE_DIR / "mapping_configs" / "debayan31415_btc_5m_top_of_book.json"
)


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


def test_api_vendor_mapping_config_inspect_validate_and_dry_run(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    sample_path = tmp_path / "btc_quotes.csv"
    sample_path.write_text(
        "\n".join(
            [
                "slug,start_time,elapsed,ask_YES,bid_YES,ask_NO,bid_NO,btc_strike,btc_current,btc_gap,timestamp_log,resolved,winner",
                "btc-up-1,2026-06-01T00:00:00Z,0,0.62,0.60,0.42,0.40,100000,100500,500,1781956800,true,YES",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    database_url = sqlite_url(tmp_path / "api_vendor_mapping.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)
    source = client.post(
        "/api/v1/vendor-data/sources",
        json={
            "vendor_name": "Kaggle",
            "dataset_name": "BTC quotes",
            "dataset_version": "sample-v1",
        },
    )
    sample = client.post(
        "/api/v1/vendor-data/samples/load",
        json={
            "vendor_source_id": source.json()["vendor_source_id"],
            "file_path": str(sample_path),
        },
    )
    sample_file_id = sample.json()["sample_file_id"]
    mapping_body = {"mapping_config_path": str(BTC_MAPPING_CONFIG)}

    inspection = client.post(
        f"/api/v1/vendor-data/samples/{sample_file_id}/inspect",
        json=mapping_body,
    )
    validation = client.post(
        f"/api/v1/vendor-data/samples/{sample_file_id}/validate",
        json=mapping_body,
    )
    dry_run = client.post(
        f"/api/v1/vendor-data/samples/{sample_file_id}/dry-run-import",
        json=mapping_body,
    )

    assert inspection.status_code == 200
    assert "bid_YES" in inspection.json()["price_columns"]
    assert validation.status_code == 200
    assert "NO_TOKEN_IDENTIFIER_COLUMN" in validation.json()["token_mapping_issues"]
    assert dry_run.status_code == 200
    assert dry_run.json()["would_create_counts"]["top_of_book_quote_snapshots"] == 1
    assert dry_run.json()["canonical_trade_prints_detected"] == 0


def test_api_vendor_sample_load_and_dry_run_support_max_rows(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    sample_path = tmp_path / "sample.csv"
    sample_path.write_text(
        "market_id,timestamp,price\n"
        "m1,2026-01-01T00:00:00Z,0.51\n"
        "m1,2026-01-01T00:01:00Z,0.52\n"
        "m1,2026-01-01T00:02:00Z,0.53\n",
        encoding="utf-8",
    )
    database_url = sqlite_url(tmp_path / "api_vendor_sampling.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)
    source = client.post(
        "/api/v1/vendor-data/sources",
        json={
            "vendor_name": "SampleVendor",
            "dataset_name": "Sampled",
            "dataset_version": "sample-v1",
        },
    )
    sample = client.post(
        "/api/v1/vendor-data/samples/load",
        json={
            "vendor_source_id": source.json()["vendor_source_id"],
            "file_path": str(sample_path),
            "max_rows": 2,
        },
    )
    sample_file_id = sample.json()["sample_file_id"]
    dry_run = client.post(
        f"/api/v1/vendor-data/samples/{sample_file_id}/dry-run-import",
        json={"sample_kind": "price_history"},
    )

    assert sample.status_code == 200
    assert sample.json()["row_count"] == 2
    assert sample.json()["metadata"]["sample_limit_applied"] is True
    assert dry_run.status_code == 200
    assert dry_run.json()["rows_examined"] == 2
