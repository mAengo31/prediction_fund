from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app

SAMPLE_DIR = Path("sample_data/vendor_samples")


def test_cli_vendor_workflow(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_vendor_data.db'}"
    runner = CliRunner()

    assert runner.invoke(app, ["init-db", "--database-url", database_url]).exit_code == 0
    source = runner.invoke(
        app,
        [
            "vendor-register-source",
            "--database-url",
            database_url,
            "--vendor-name",
            "SampleVendor",
            "--dataset-name",
            "Polymarket history",
            "--dataset-version",
            "sample-v1",
            "--license-status",
            "SAMPLE_ONLY",
        ],
    )
    assert source.exit_code == 0
    vendor_source_id = next(
        line.split("|", maxsplit=1)[0].strip()
        for line in source.output.splitlines()
        if line.startswith("vendor_source_") and not line.startswith("vendor_source_id")
    )
    sample = runner.invoke(
        app,
        [
            "vendor-load-sample",
            "--database-url",
            database_url,
            "--vendor-source-id",
            vendor_source_id,
            "--file-path",
            str(SAMPLE_DIR / "polymarket_orderbook_sample.jsonl"),
        ],
    )
    assert sample.exit_code == 0
    sample_file_id = next(
        line.split("|", maxsplit=1)[0].strip()
        for line in sample.output.splitlines()
        if line.startswith("vendor_sample_")
    )
    inspect = runner.invoke(
        app,
        [
            "vendor-inspect-sample",
            "--database-url",
            database_url,
            "--sample-file-id",
            sample_file_id,
        ],
    )
    validate = runner.invoke(
        app,
        [
            "vendor-validate-sample",
            "--database-url",
            database_url,
            "--sample-file-id",
            sample_file_id,
        ],
    )
    dry_run = runner.invoke(
        app,
        [
            "vendor-dry-run-import",
            "--database-url",
            database_url,
            "--sample-file-id",
            sample_file_id,
            "--sample-kind",
            "orderbook",
        ],
    )
    evaluate = runner.invoke(
        app,
        [
            "vendor-evaluate",
            "--database-url",
            database_url,
            "--vendor-source-id",
            vendor_source_id,
            "--sample-file-id",
            sample_file_id,
        ],
    )
    reports = runner.invoke(
        app,
        [
            "vendor-reports",
            "--database-url",
            database_url,
            "--vendor-source-id",
            vendor_source_id,
        ],
    )

    assert inspect.exit_code == 0
    assert "token_id" in inspect.output
    assert validate.exit_code == 0
    assert "PASS" in validate.output or "WARNING" in validate.output
    assert dry_run.exit_code == 0
    assert "vendor_dry_run_" in dry_run.output
    assert evaluate.exit_code == 0
    assert "vendor_eval_" in evaluate.output
    assert reports.exit_code == 0
    assert "vendor_eval_" in reports.output
