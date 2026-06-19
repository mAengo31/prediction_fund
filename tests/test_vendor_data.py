from __future__ import annotations

from pathlib import Path

import pytest

from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.vendor_data.enums import VendorLicenseStatus, VendorSampleKind
from prediction_desk.vendor_data.file_loader import (
    VendorFileLoaderError,
    load_rows,
    validate_local_file,
)
from prediction_desk.vendor_data.models import (
    VendorDatasetSource,
    VendorDatasetSourceCreate,
    VendorDryRunImportRequest,
    VendorEvaluateRequest,
    VendorSampleLoadRequest,
)
from prediction_desk.vendor_data.service import VendorDataService

SAMPLE_DIR = Path("sample_data/vendor_samples")


def _service(database_url: str) -> VendorDataService:
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    session = session_factory()
    return VendorDataService(PredictionMarketRepository(session))


def _source(service: VendorDataService) -> VendorDatasetSource:
    return service.register_source(
        VendorDatasetSourceCreate(
            vendor_name="SampleVendor",
            dataset_name="Polymarket history",
            dataset_version="sample-v1",
            license_status=VendorLicenseStatus.SAMPLE_ONLY,
        )
    )


def test_file_loader_rejects_url() -> None:
    with pytest.raises(VendorFileLoaderError, match="vendor_file_path_must_be_local"):
        load_rows("https://example.com/sample.csv")


def test_file_loader_rejects_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "large.csv"
    path.write_text("timestamp,price\n2026-01-01T00:00:00Z,0.5\n", encoding="utf-8")

    with pytest.raises(VendorFileLoaderError, match="vendor_sample_file_too_large"):
        validate_local_file(str(path), max_size_mb=0)


def test_csv_and_jsonl_samples_load() -> None:
    csv_rows = load_rows(str(SAMPLE_DIR / "polymarket_price_history_sample.csv"))
    jsonl_rows = load_rows(str(SAMPLE_DIR / "polymarket_orderbook_sample.jsonl"))

    assert len(csv_rows) == 3
    assert len(jsonl_rows) == 4


def test_schema_validation_dry_run_and_evaluation(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'vendor_data.db'}"
    service = _service(database_url)
    source = _source(service)
    good = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(SAMPLE_DIR / "polymarket_orderbook_sample.jsonl"),
        )
    )
    bad = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(SAMPLE_DIR / "bad_missing_token_sample.csv"),
        )
    )

    good_inspection = service.inspect_sample(good.sample_file_id)
    bad_validation = service.validate_sample(bad.sample_file_id)
    dry_run = service.dry_run_import(
        good.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.ORDERBOOK),
    )
    good_eval = service.evaluate(
        VendorEvaluateRequest(
            vendor_source_id=source.vendor_source_id,
            sample_file_ids=[good.sample_file_id],
        )
    )
    bad_eval = service.evaluate(
        VendorEvaluateRequest(
            vendor_source_id=source.vendor_source_id,
            sample_file_ids=[bad.sample_file_id],
        )
    )

    assert "token_id" in good_inspection.token_identifier_columns
    assert "price" in good_inspection.price_columns
    assert bad_validation.price_issues
    assert bad_validation.timestamp_issues
    assert dry_run.canonical_orderbooks_detected == 4
    assert dry_run.would_create_counts["orderbook_snapshots"] == 4
    assert dry_run.canonical_trade_prints_detected == 0
    assert dry_run.would_create_counts["trade_prints"] == 0
    assert "SUPPRESSED_TRADE_COUNT_MISSING_TRADE_EVIDENCE" in dry_run.warnings
    assert good_eval.coverage_score > bad_eval.coverage_score
    assert good_eval.token_mapping_score > bad_eval.token_mapping_score


def test_dry_run_counts_price_snapshots_and_skips_invalid_rows(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'vendor_prices.db'}"
    service = _service(database_url)
    source = _source(service)
    good = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(SAMPLE_DIR / "polymarket_price_history_sample.csv"),
        )
    )
    bad = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(SAMPLE_DIR / "bad_missing_token_sample.csv"),
        )
    )

    good_run = service.dry_run_import(
        good.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.PRICE_HISTORY),
    )
    bad_run = service.dry_run_import(
        bad.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.PRICE_HISTORY),
    )

    assert good_run.canonical_price_snapshots_detected == 3
    assert good_run.canonical_trade_prints_detected == 0
    assert good_run.canonical_orderbooks_detected == 0
    assert sum(bad_run.would_skip_counts.values()) >= 1


def test_dry_run_counts_trades_without_orderbook_overcount(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'vendor_trades.db'}"
    service = _service(database_url)
    source = _source(service)
    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(SAMPLE_DIR / "polymarket_trades_sample.csv"),
        )
    )

    dry_run = service.dry_run_import(
        sample.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.TRADES),
    )

    assert dry_run.canonical_trade_prints_detected == 2
    assert dry_run.would_create_counts["trade_prints"] == 2
    assert dry_run.canonical_orderbooks_detected == 0
    assert dry_run.would_create_counts["orderbook_snapshots"] == 0
    assert "SUPPRESSED_ORDERBOOK_COUNT_MISSING_BOOK_EVIDENCE" in dry_run.warnings


def test_mixed_sample_counts_multiple_types_only_with_evidence(tmp_path: Path) -> None:
    path = tmp_path / "mixed_vendor_sample.csv"
    path.write_text(
        "\n".join(
            [
                "condition_id,token_id,timestamp,price,size,side,level,trade_id,observed_at,captured_at,available_at",
                "cond1,tok_yes,2026-06-01T00:00:00Z,0.52,20,bid,1,,2026-06-01T00:00:00Z,2026-06-01T00:00:01Z,2026-06-01T00:00:01Z",
                "cond1,tok_yes,2026-06-01T00:01:00Z,0.53,5,buy,,trade-1,2026-06-01T00:01:00Z,2026-06-01T00:01:01Z,2026-06-01T00:01:01Z",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    database_url = f"sqlite:///{tmp_path / 'vendor_mixed.db'}"
    service = _service(database_url)
    source = _source(service)
    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(path),
        )
    )

    dry_run = service.dry_run_import(
        sample.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.MIXED),
    )

    assert dry_run.canonical_orderbooks_detected == 1
    assert dry_run.canonical_trade_prints_detected == 1
    assert dry_run.canonical_price_snapshots_detected == 2


def test_ambiguous_price_size_rows_warn_and_under_count(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous_price_size.csv"
    path.write_text(
        "\n".join(
            [
                "condition_id,token_id,timestamp,price,size,observed_at,captured_at,available_at",
                "cond1,tok_yes,2026-06-01T00:00:00Z,0.52,20,2026-06-01T00:00:00Z,2026-06-01T00:00:01Z,2026-06-01T00:00:01Z",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    database_url = f"sqlite:///{tmp_path / 'vendor_ambiguous.db'}"
    service = _service(database_url)
    source = _source(service)
    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(path),
        )
    )

    dry_run = service.dry_run_import(
        sample.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.MIXED),
    )

    assert dry_run.canonical_orderbooks_detected == 0
    assert dry_run.canonical_trade_prints_detected == 0
    assert dry_run.canonical_price_snapshots_detected == 0
    assert "AMBIGUOUS_PRICE_SIZE_ROWS" in dry_run.warnings
    assert "SUPPRESSED_TRADE_COUNT_MISSING_TRADE_EVIDENCE" in dry_run.warnings
    assert "SAMPLE_KIND_SCHEMA_MISMATCH" in dry_run.warnings
