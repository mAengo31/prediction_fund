"""Vendor dataset evaluation scoring."""

from __future__ import annotations

from datetime import datetime

from prediction_desk.vendor_data.enums import VendorEvaluationStatus, VendorLicenseStatus
from prediction_desk.vendor_data.models import (
    VendorDatasetSource,
    VendorDataValidationReport,
    VendorEvaluationReport,
    VendorImportDryRun,
    VendorSchemaInspection,
)


def build_vendor_evaluation_report(
    *,
    evaluation_report_id: str,
    source: VendorDatasetSource,
    sample_file_ids: list[str],
    inspections: list[VendorSchemaInspection],
    validation_reports: list[VendorDataValidationReport],
    dry_runs: list[VendorImportDryRun],
    created_at: datetime,
) -> VendorEvaluationReport:
    coverage_score = _coverage_score(inspections, dry_runs)
    token_score = _token_mapping_score(inspections, validation_reports)
    timestamp_score = _timestamp_score(inspections, validation_reports)
    orderbook_score = _orderbook_score(inspections, dry_runs)
    price_score = _price_score(inspections, dry_runs, validation_reports)
    replay_score = _replay_score(validation_reports, timestamp_score)
    license_score = _license_score(source.license_status)
    scores = [
        coverage_score,
        token_score,
        timestamp_score,
        orderbook_score,
        price_score,
        replay_score,
        license_score,
    ]
    average = sum(scores) // len(scores)
    strengths: list[str] = []
    weaknesses: list[str] = []
    questions: list[str] = []

    if token_score >= 80:
        strengths.append("Token or asset identifiers are present and usable.")
    else:
        weaknesses.append("Token mapping is incomplete or unclear.")
        questions.append("Which fields are authoritative CLOB token or asset identifiers?")
    if orderbook_score >= 80:
        strengths.append("Orderbook-like rows are present.")
    else:
        weaknesses.append("Orderbook depth is missing or not directly usable.")
        questions.append("Can the vendor provide token-level bid/ask depth snapshots?")
    if price_score >= 80:
        strengths.append("Probability-style price history appears usable.")
    else:
        weaknesses.append("Price history is sparse or has validation issues.")
    if replay_score < 80:
        weaknesses.append("Point-in-time semantics need clarification.")
        questions.append(
            "Which timestamp should be treated as observed_at, captured_at, and available_at?"
        )
    if license_score < 70:
        questions.append(
            "What license terms allow internal research, replay, and derived features?"
        )

    if average >= 80 and token_score >= 70 and replay_score >= 70:
        overall = VendorEvaluationStatus.PROMISING
        recommendation = (
            "Promising sample for further vendor due diligence; keep import dry-run only "
            "until terms and timestamp semantics are confirmed."
        )
    elif average >= 55:
        overall = VendorEvaluationStatus.NEEDS_CLARIFICATION
        recommendation = (
            "Needs clarification before purchase or production import; request identifier, "
            "timestamp, and license details."
        )
    elif average >= 35:
        overall = VendorEvaluationStatus.HOLD
        recommendation = (
            "Hold pending better samples; current files are not strong enough for canonical "
            "import planning."
        )
    else:
        overall = VendorEvaluationStatus.REJECT_SAMPLE
        recommendation = (
            "Reject this sample for now; it does not meet replay-safe evaluation requirements."
        )

    return VendorEvaluationReport(
        evaluation_report_id=evaluation_report_id,
        vendor_source_id=source.vendor_source_id,
        created_at=created_at,
        sample_file_ids=sample_file_ids,
        overall_status=overall,
        coverage_score=coverage_score,
        token_mapping_score=token_score,
        timestamp_quality_score=timestamp_score,
        orderbook_quality_score=orderbook_score,
        price_history_quality_score=price_score,
        replay_safety_score=replay_score,
        license_readiness_score=license_score,
        strengths=strengths,
        weaknesses=weaknesses,
        questions_for_vendor=questions,
        recommendation=recommendation,
        metadata={
            "evaluation_version": "vendor_evaluation_report_v1",
            "average_score": average,
            "dry_run_only": True,
        },
    )


def _coverage_score(
    inspections: list[VendorSchemaInspection],
    dry_runs: list[VendorImportDryRun],
) -> int:
    capabilities = 0
    if any(inspection.market_identifier_columns for inspection in inspections):
        capabilities += 20
    if any(inspection.token_identifier_columns for inspection in inspections):
        capabilities += 20
    if any(run.canonical_price_snapshots_detected for run in dry_runs):
        capabilities += 20
    if any(run.canonical_orderbooks_detected for run in dry_runs):
        capabilities += 20
    if any(
        run.canonical_trade_prints_detected or run.canonical_resolution_events_detected
        for run in dry_runs
    ):
        capabilities += 20
    return min(100, capabilities)


def _token_mapping_score(
    inspections: list[VendorSchemaInspection],
    reports: list[VendorDataValidationReport],
) -> int:
    if not any(inspection.token_identifier_columns for inspection in inspections):
        return 30 if any(inspection.market_identifier_columns for inspection in inspections) else 0
    issue_count = sum(len(report.token_mapping_issues) for report in reports)
    return max(20, 100 - min(issue_count * 10, 80))


def _timestamp_score(
    inspections: list[VendorSchemaInspection],
    reports: list[VendorDataValidationReport],
) -> int:
    if not any(inspection.timestamp_columns for inspection in inspections):
        return 0
    issue_count = sum(len(report.timestamp_issues) for report in reports)
    return max(20, 100 - min(issue_count * 15, 80))


def _orderbook_score(
    inspections: list[VendorSchemaInspection],
    dry_runs: list[VendorImportDryRun],
) -> int:
    if not any(inspection.orderbook_columns for inspection in inspections):
        return 20
    detected = sum(run.canonical_orderbooks_detected for run in dry_runs)
    return 100 if detected else 55


def _price_score(
    inspections: list[VendorSchemaInspection],
    dry_runs: list[VendorImportDryRun],
    reports: list[VendorDataValidationReport],
) -> int:
    if not any(inspection.price_columns for inspection in inspections):
        return 10
    issue_count = sum(len(report.price_issues) for report in reports)
    detected = sum(run.canonical_price_snapshots_detected for run in dry_runs)
    base = 100 if detected else 50
    return max(10, base - min(issue_count * 15, 80))


def _replay_score(reports: list[VendorDataValidationReport], timestamp_score: int) -> int:
    issue_count = sum(len(report.point_in_time_issues) for report in reports)
    return max(0, min(100, timestamp_score - min(issue_count * 10, 50)))


def _license_score(status: VendorLicenseStatus) -> int:
    return {
        VendorLicenseStatus.APPROVED: 100,
        VendorLicenseStatus.INTERNAL_RESEARCH: 75,
        VendorLicenseStatus.SAMPLE_ONLY: 50,
        VendorLicenseStatus.COMMERCIAL_RESTRICTED: 45,
        VendorLicenseStatus.UNKNOWN: 20,
    }[status]
