from __future__ import annotations

from datetime import UTC, datetime
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
from prediction_desk.vendor_data.mapping_config import (
    VendorSchemaMappingConfigError,
    load_vendor_schema_mapping_config,
    validate_vendor_schema_mapping_config,
)
from prediction_desk.vendor_data.models import (
    VendorDatasetSource,
    VendorDatasetSourceCreate,
    VendorDryRunImportRequest,
    VendorEvaluateRequest,
    VendorSampleInspectRequest,
    VendorSampleLoadRequest,
    VendorSampleValidateRequest,
)
from prediction_desk.vendor_data.schema_inspector import inspect_vendor_schema
from prediction_desk.vendor_data.service import VendorDataService

SAMPLE_DIR = Path("sample_data/vendor_samples")
BTC_MAPPING_CONFIG = (
    SAMPLE_DIR / "mapping_configs" / "debayan31415_btc_5m_top_of_book.json"
)


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


def test_mapping_config_loader_rejects_url() -> None:
    with pytest.raises(VendorSchemaMappingConfigError, match="vendor_file_path_must_be_local"):
        load_vendor_schema_mapping_config("https://example.com/mapping.json")


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


def test_csv_and_jsonl_sampling_limits_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "market_id,timestamp,price\n"
        "m1,2026-01-01T00:00:00Z,0.51\n"
        "m1,2026-01-01T00:01:00Z,0.52\n"
        "m1,2026-01-01T00:02:00Z,0.53\n",
        encoding="utf-8",
    )
    jsonl_path = tmp_path / "sample.jsonl"
    jsonl_path.write_text(
        '{"market_id":"m1","timestamp":"2026-01-01T00:00:00Z","price":"0.51"}\n'
        '{"market_id":"m1","timestamp":"2026-01-01T00:01:00Z","price":"0.52"}\n'
        '{"market_id":"m1","timestamp":"2026-01-01T00:02:00Z","price":"0.53"}\n',
        encoding="utf-8",
    )

    assert [row["price"] for row in load_rows(str(csv_path), max_rows=2)] == ["0.51", "0.52"]
    assert [row["price"] for row in load_rows(str(jsonl_path), max_rows=1)] == ["0.51"]


def test_vendor_sample_load_records_sampling_metadata(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        "market_id,timestamp,price\n"
        "m1,2026-01-01T00:00:00Z,0.51\n"
        "m1,2026-01-01T00:01:00Z,0.52\n"
        "m1,2026-01-01T00:02:00Z,0.53\n",
        encoding="utf-8",
    )
    database_url = f"sqlite:///{tmp_path / 'vendor_sampled.db'}"
    service = _service(database_url)
    source = _source(service)

    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(path),
            max_rows=2,
        )
    )
    dry_run = service.dry_run_import(
        sample.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.PRICE_HISTORY),
    )

    assert sample.row_count == 2
    assert sample.metadata["sampled_row_count"] == 2
    assert sample.metadata["sample_limit_applied"] is True
    assert dry_run.rows_examined == 2
    assert dry_run.canonical_price_snapshots_detected == 2


def test_embedded_data_json_detects_orderbook_evidence(tmp_path: Path) -> None:
    path = tmp_path / "nested_orderbook.jsonl"
    path.write_text(
        '{"timestamp_received":1774224376603,'
        '"timestamp_created_at":1774224380526,'
        '"market_id":"0xmarket",'
        '"update_type":"book_snapshot",'
        '"data":"{\\"token_id\\":\\"token-1\\",\\"side\\":\\"YES\\",'
        '\\"best_bid\\":\\"0.45\\",\\"best_ask\\":\\"0.46\\",'
        '\\"bids\\":[[\\"0.45\\",\\"10\\"]],'
        '\\"asks\\":[[\\"0.46\\",\\"12\\"]]}"}\n',
        encoding="utf-8",
    )
    database_url = f"sqlite:///{tmp_path / 'vendor_nested_orderbook.db'}"
    service = _service(database_url)
    source = _source(service)
    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(path),
        )
    )

    inspection = service.inspect_sample(sample.sample_file_id)
    dry_run = service.dry_run_import(
        sample.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.ORDERBOOK),
    )

    assert "data_token_id" in inspection.token_identifier_columns
    assert {"data_best_bid", "data_best_ask"}.issubset(set(inspection.price_columns))
    assert {"data_bids", "data_asks"}.issubset(set(inspection.orderbook_columns))
    assert dry_run.canonical_orderbooks_detected == 1
    assert dry_run.canonical_price_snapshots_detected == 1


def test_schema_inspector_detects_strong_timestamp_aliases() -> None:
    inspection = inspect_vendor_schema(
        schema_inspection_id="vendor_schema_timestamp_alias_test",
        sample_file_id="vendor_sample_timestamp_alias_test",
        inspected_at=datetime(2026, 6, 20, tzinfo=UTC),
        rows=[
            {
                "market_id": "123",
                "ts": "2026-06-20T12:00:00Z",
                "datetime": "2026-06-20T12:00:00Z",
                "date_time": "2026-06-20T12:00:00Z",
                "created_time": "2026-06-20T12:00:00Z",
                "unix_timestamp": "1781956800",
                "volume": "12345",
                "price": "0.52",
            }
        ],
    )

    assert {
        "ts",
        "datetime",
        "date_time",
        "created_time",
        "unix_timestamp",
    }.issubset(set(inspection.timestamp_columns))
    assert "volume" not in inspection.timestamp_columns


def test_mapping_config_validates_referenced_columns() -> None:
    config = load_vendor_schema_mapping_config(str(BTC_MAPPING_CONFIG))

    warnings = validate_vendor_schema_mapping_config(
        config,
        ["slug", "start_time", "bid_YES", "ask_YES", "resolved"],
    )

    assert "MAPPING_COLUMN_NOT_FOUND:bid_NO" in warnings
    assert "MAPPING_COLUMN_NOT_FOUND:ask_NO" in warnings
    assert "MAPPING_TOKEN_IDENTIFIER_NOT_CONFIGURED" in warnings


def test_btc_mapping_config_detects_top_of_book_quotes(tmp_path: Path) -> None:
    path = _write_btc_top_of_book_sample(tmp_path / "btc_quotes.csv")
    database_url = f"sqlite:///{tmp_path / 'vendor_btc_mapping.db'}"
    service = _service(database_url)
    source = _source(service)
    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(path),
        )
    )

    inspection = service.inspect_sample(
        sample.sample_file_id,
        VendorSampleInspectRequest(mapping_config_path=str(BTC_MAPPING_CONFIG)),
    )

    assert "slug" in inspection.market_identifier_columns
    assert "start_time" in inspection.timestamp_columns
    assert {"bid_YES", "ask_YES", "bid_NO", "ask_NO"}.issubset(
        set(inspection.price_columns)
    )
    assert "resolved" in inspection.resolution_columns
    assert inspection.metadata["mapping_config"]["mapping_name"] == (
        "debayan31415_btc_5m_top_of_book"
    )


def test_mapped_quote_validation_checks_bid_ask_bounds(tmp_path: Path) -> None:
    path = _write_btc_top_of_book_sample(
        tmp_path / "btc_crossed_quotes.csv",
        yes_bid="0.62",
        yes_ask="0.60",
    )
    database_url = f"sqlite:///{tmp_path / 'vendor_btc_validation.db'}"
    service = _service(database_url)
    source = _source(service)
    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(path),
        )
    )

    report = service.validate_sample(
        sample.sample_file_id,
        VendorSampleValidateRequest(mapping_config_path=str(BTC_MAPPING_CONFIG)),
    )

    assert "ROW_1_YES_BID_GT_ASK" in report.price_issues
    assert "NO_TOKEN_IDENTIFIER_COLUMN" in report.token_mapping_issues


def test_dry_run_with_btc_mapping_counts_top_of_book_not_trades_or_tokens(
    tmp_path: Path,
) -> None:
    path = _write_btc_top_of_book_sample(tmp_path / "btc_quotes.csv")
    database_url = f"sqlite:///{tmp_path / 'vendor_btc_dry_run.db'}"
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
        VendorDryRunImportRequest(mapping_config_path=str(BTC_MAPPING_CONFIG)),
    )
    evaluation = service.evaluate(
        VendorEvaluateRequest(
            vendor_source_id=source.vendor_source_id,
            sample_file_ids=[sample.sample_file_id],
            mapping_config_path=str(BTC_MAPPING_CONFIG),
        )
    )

    assert dry_run.canonical_markets_detected == 2
    assert dry_run.canonical_price_snapshots_detected == 3
    assert dry_run.would_create_counts["top_of_book_quote_snapshots"] == 3
    assert dry_run.would_create_counts["token_mappings"] == 0
    assert dry_run.canonical_orderbooks_detected == 0
    assert dry_run.canonical_trade_prints_detected == 0
    assert dry_run.canonical_resolution_events_detected == 1
    assert "TOKEN_MAPPING_NOT_DETECTED" in dry_run.warnings
    assert "TOP_OF_BOOK_QUOTES_NOT_FULL_ORDERBOOK_DEPTH" in dry_run.warnings
    assert evaluation.coverage_score >= 60
    assert evaluation.token_mapping_score == 30


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


def test_dry_run_accepts_unix_timestamp_alias_for_price_history(tmp_path: Path) -> None:
    path = tmp_path / "unix_timestamp_prices.csv"
    path.write_text(
        "\n".join(
            [
                "market_id,unix_timestamp,price",
                "market-1,1781956800,0.52",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    database_url = f"sqlite:///{tmp_path / 'vendor_unix_timestamp.db'}"
    service = _service(database_url)
    source = _source(service)
    sample = service.load_sample(
        VendorSampleLoadRequest(
            vendor_source_id=source.vendor_source_id,
            file_path=str(path),
        )
    )

    inspection = service.inspect_sample(sample.sample_file_id)
    validation = service.validate_sample(sample.sample_file_id)
    dry_run = service.dry_run_import(
        sample.sample_file_id,
        VendorDryRunImportRequest(sample_kind=VendorSampleKind.PRICE_HISTORY),
    )

    assert "unix_timestamp" in inspection.timestamp_columns
    assert not validation.timestamp_issues
    assert dry_run.canonical_price_snapshots_detected == 1
    assert dry_run.would_skip_counts == {}


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


def _write_btc_top_of_book_sample(
    path: Path,
    *,
    yes_bid: str = "0.60",
    yes_ask: str = "0.62",
) -> Path:
    path.write_text(
        "\n".join(
            [
                "slug,start_time,elapsed,ask_YES,bid_YES,ask_NO,bid_NO,btc_strike,btc_current,btc_gap,timestamp_log,resolved,winner",
                f"btc-up-1,2026-06-01T00:00:00Z,0,{yes_ask},{yes_bid},0.42,0.40,100000,100500,500,1781956800,false,",
                "btc-up-1,2026-06-01T00:00:00Z,300,0.64,0.61,0.41,0.38,100000,100600,600,1781957100,true,YES",
                "btc-up-2,2026-06-01T00:05:00Z,0,0.55,0.53,0.49,0.45,101000,100900,-100,1781957400,false,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path
