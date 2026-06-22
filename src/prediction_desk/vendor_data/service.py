"""Service layer for vendor dataset sample evaluation."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.vendor_data.dry_run_import import dry_run_vendor_import
from prediction_desk.vendor_data.evaluation import build_vendor_evaluation_report
from prediction_desk.vendor_data.file_loader import (
    VendorFileLoaderError,
    compute_file_hash,
    detect_file_type,
    estimate_total_rows_if_cheap,
    load_rows,
    schema_summary,
    validate_local_file,
)
from prediction_desk.vendor_data.mapping_config import (
    VendorSchemaMappingConfigError,
    load_vendor_schema_mapping_config,
)
from prediction_desk.vendor_data.models import (
    VendorDatasetSource,
    VendorDatasetSourceCreate,
    VendorDataValidationReport,
    VendorDryRunImportRequest,
    VendorEvaluateRequest,
    VendorEvaluationReport,
    VendorImportDryRun,
    VendorSampleFile,
    VendorSampleInspectRequest,
    VendorSampleLoadRequest,
    VendorSampleValidateRequest,
    VendorSchemaInspection,
    VendorSchemaMappingConfig,
)
from prediction_desk.vendor_data.registry import build_vendor_source
from prediction_desk.vendor_data.schema_inspector import inspect_vendor_schema
from prediction_desk.vendor_data.validators import validate_vendor_rows


class VendorDataServiceError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class VendorDataService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def register_source(self, request: VendorDatasetSourceCreate) -> VendorDatasetSource:
        source = build_vendor_source(
            vendor_name=request.vendor_name,
            dataset_name=request.dataset_name,
            dataset_version=request.dataset_version,
            contact_url=request.contact_url,
            license_status=request.license_status,
            supported_file_types=request.supported_file_types,
            metadata=request.metadata,
        )
        return self.repo.save_vendor_dataset_source(source)

    def list_sources(self, *, limit: int = 500, offset: int = 0) -> list[VendorDatasetSource]:
        return self.repo.list_vendor_dataset_sources(limit=limit, offset=offset)

    def get_source(self, vendor_source_id: str) -> VendorDatasetSource:
        source = self.repo.get_vendor_dataset_source(vendor_source_id)
        if source is None:
            raise VendorDataServiceError("vendor_source_not_found")
        return source

    def load_sample(self, request: VendorSampleLoadRequest) -> VendorSampleFile:
        self.get_source(request.vendor_source_id)
        try:
            path = validate_local_file(
                request.file_path,
                max_size_mb=request.max_size_mb,
                allow_sampling=request.max_rows is not None,
            )
            file_type = detect_file_type(path)
            rows = load_rows(
                str(path),
                max_size_mb=request.max_size_mb,
                max_rows=request.max_rows,
            )
        except VendorFileLoaderError as exc:
            raise VendorDataServiceError(exc.code) from exc
        file_hash = compute_file_hash(path)
        total_row_count = estimate_total_rows_if_cheap(str(path))
        sample_limit_applied = request.max_rows is not None and (
            len(rows) == request.max_rows
            or (total_row_count is not None and total_row_count > len(rows))
        )
        sample = VendorSampleFile(
            sample_file_id=_stable_id(
                "vendor_sample",
                request.vendor_source_id,
                file_hash,
                f"max_rows:{request.max_rows or 'all'}",
            ),
            vendor_source_id=request.vendor_source_id,
            file_name=path.name,
            file_type=file_type,
            local_path=str(path),
            imported_at=datetime.now(tz=UTC),
            file_size_bytes=path.stat().st_size,
            file_hash=file_hash,
            row_count=len(rows),
            schema_summary=schema_summary(rows),
            metadata={
                **request.metadata,
                "max_size_mb": request.max_size_mb,
                "max_rows": request.max_rows,
                "original_path": request.file_path,
                "archived_original_file": False,
                "sampled_row_count": len(rows),
                "total_row_count": total_row_count,
                "total_row_count_known": total_row_count is not None,
                "sample_limit_applied": sample_limit_applied,
            },
        )
        return self.repo.save_vendor_sample_file(sample)

    def list_samples(
        self,
        *,
        vendor_source_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[VendorSampleFile]:
        return self.repo.list_vendor_sample_files(
            vendor_source_id=vendor_source_id,
            limit=limit,
            offset=offset,
        )

    def get_sample(self, sample_file_id: str) -> VendorSampleFile:
        sample = self.repo.get_vendor_sample_file(sample_file_id)
        if sample is None:
            raise VendorDataServiceError("vendor_sample_file_not_found")
        return sample

    def inspect_sample(
        self,
        sample_file_id: str,
        request: VendorSampleInspectRequest | None = None,
    ) -> VendorSchemaInspection:
        sample = self.get_sample(sample_file_id)
        effective_max_rows = _effective_max_rows(
            persisted_max_rows=sample.metadata.get("max_rows"),
            requested_max_rows=request.max_rows if request else None,
        )
        rows = self._load_sample_rows(sample, max_rows=request.max_rows if request else None)
        mapping_config = self._load_mapping_config(
            request.mapping_config_path if request else None
        )
        inspection = inspect_vendor_schema(
            schema_inspection_id=_stable_id(
                "vendor_schema",
                sample.sample_file_id,
                sample.file_hash,
                _mapping_identity(mapping_config),
                _row_limit_identity(effective_max_rows),
            ),
            sample_file_id=sample.sample_file_id,
            rows=rows,
            inspected_at=datetime.now(tz=UTC),
            mapping_config=mapping_config,
        )
        return self.repo.save_vendor_schema_inspection(inspection)

    def validate_sample(
        self,
        sample_file_id: str,
        request: VendorSampleValidateRequest | None = None,
    ) -> VendorDataValidationReport:
        sample = self.get_sample(sample_file_id)
        effective_max_rows = _effective_max_rows(
            persisted_max_rows=sample.metadata.get("max_rows"),
            requested_max_rows=request.max_rows if request else None,
        )
        mapping_config = self._load_mapping_config(
            request.mapping_config_path if request else None
        )
        inspection = self.inspect_sample(
            sample_file_id,
            VendorSampleInspectRequest(
                mapping_config_path=request.mapping_config_path if request else None,
            ),
        )
        rows = self._load_sample_rows(sample, max_rows=request.max_rows if request else None)
        report = validate_vendor_rows(
            validation_report_id=_stable_id(
                "vendor_validation",
                sample.sample_file_id,
                sample.file_hash,
                _mapping_identity(mapping_config),
                _row_limit_identity(effective_max_rows),
            ),
            sample_file_id=sample.sample_file_id,
            rows=rows,
            inspection=inspection,
            created_at=datetime.now(tz=UTC),
            mapping_config=mapping_config,
        )
        return self.repo.save_vendor_data_validation_report(report)

    def dry_run_import(
        self,
        sample_file_id: str,
        request: VendorDryRunImportRequest | None = None,
    ) -> VendorImportDryRun:
        sample = self.get_sample(sample_file_id)
        effective_max_rows = _effective_max_rows(
            persisted_max_rows=sample.metadata.get("max_rows"),
            requested_max_rows=request.max_rows if request else None,
        )
        mapping_config = self._load_mapping_config(
            request.mapping_config_path if request else None
        )
        inspection = self.inspect_sample(
            sample_file_id,
            VendorSampleInspectRequest(
                mapping_config_path=request.mapping_config_path if request else None,
            ),
        )
        rows = self._load_sample_rows(sample, max_rows=request.max_rows if request else None)
        sample_kind = request.sample_kind if request else None
        dry_run = dry_run_vendor_import(
            dry_run_id=_stable_id(
                "vendor_dry_run",
                sample.sample_file_id,
                sample.file_hash,
                sample_kind.value if sample_kind else "auto",
                _mapping_identity(mapping_config),
                _row_limit_identity(effective_max_rows),
            ),
            sample_file_id=sample.sample_file_id,
            rows=rows,
            inspection=inspection,
            created_at=datetime.now(tz=UTC),
            sample_kind=sample_kind,
            mapping_config=mapping_config,
        )
        return self.repo.save_vendor_import_dry_run(dry_run)

    def evaluate(self, request: VendorEvaluateRequest) -> VendorEvaluationReport:
        source = self.get_source(request.vendor_source_id)
        sample_ids = list(request.sample_file_ids)
        if not sample_ids:
            sample_ids = [
                sample.sample_file_id
                for sample in self.list_samples(vendor_source_id=source.vendor_source_id, limit=500)
            ]
        if not sample_ids:
            raise VendorDataServiceError("vendor_evaluation_requires_samples")

        inspections: list[VendorSchemaInspection] = []
        validations: list[VendorDataValidationReport] = []
        dry_runs: list[VendorImportDryRun] = []
        for sample_id in sample_ids:
            sample = self.get_sample(sample_id)
            if sample.vendor_source_id != source.vendor_source_id:
                raise VendorDataServiceError("vendor_sample_source_mismatch")
            inspections.append(
                self.inspect_sample(
                    sample_id,
                    VendorSampleInspectRequest(
                        mapping_config_path=request.mapping_config_path,
                    ),
                )
            )
            validations.append(
                self.validate_sample(
                    sample_id,
                    VendorSampleValidateRequest(
                        mapping_config_path=request.mapping_config_path,
                    ),
                )
            )
            dry_runs.append(
                self.dry_run_import(
                    sample_id,
                    VendorDryRunImportRequest(
                        mapping_config_path=request.mapping_config_path,
                    ),
                )
            )

        report = build_vendor_evaluation_report(
            evaluation_report_id=_stable_id(
                "vendor_eval",
                source.vendor_source_id,
                ",".join(sorted(sample_ids)),
                request.mapping_config_path or "auto_mapping",
                datetime.now(tz=UTC).isoformat(),
            ),
            source=source,
            sample_file_ids=sample_ids,
            inspections=inspections,
            validation_reports=validations,
            dry_runs=dry_runs,
            created_at=datetime.now(tz=UTC),
        )
        return self.repo.save_vendor_evaluation_report(report)

    def list_reports(
        self,
        *,
        vendor_source_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VendorEvaluationReport]:
        return self.repo.list_vendor_evaluation_reports(
            vendor_source_id=vendor_source_id,
            limit=limit,
            offset=offset,
        )

    def get_report(self, evaluation_report_id: str) -> VendorEvaluationReport:
        report = self.repo.get_vendor_evaluation_report(evaluation_report_id)
        if report is None:
            raise VendorDataServiceError("vendor_evaluation_report_not_found")
        return report

    def _load_sample_rows(
        self,
        sample: VendorSampleFile,
        *,
        max_rows: int | None = None,
    ) -> list[dict[str, object]]:
        max_size_mb = int(sample.metadata.get("max_size_mb", 100))
        effective_max_rows = _effective_max_rows(
            persisted_max_rows=sample.metadata.get("max_rows"),
            requested_max_rows=max_rows,
        )
        try:
            return load_rows(
                sample.local_path,
                max_size_mb=max_size_mb,
                max_rows=effective_max_rows,
            )
        except VendorFileLoaderError as exc:
            raise VendorDataServiceError(exc.code) from exc

    def _load_mapping_config(
        self,
        mapping_config_path: str | None,
    ) -> VendorSchemaMappingConfig | None:
        if not mapping_config_path:
            return None
        try:
            return load_vendor_schema_mapping_config(mapping_config_path)
        except VendorSchemaMappingConfigError as exc:
            raise VendorDataServiceError(exc.code) from exc


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _mapping_identity(mapping_config: VendorSchemaMappingConfig | None) -> str:
    if mapping_config is None:
        return "auto_mapping"
    return mapping_config.mapping_name


def _row_limit_identity(max_rows: int | None) -> str:
    return f"rows:{max_rows or 'all'}"


def _effective_max_rows(
    *,
    persisted_max_rows: object,
    requested_max_rows: int | None,
) -> int | None:
    persisted = _coerce_positive_int(persisted_max_rows)
    if persisted is not None and requested_max_rows is not None:
        return min(persisted, requested_max_rows)
    return requested_max_rows if requested_max_rows is not None else persisted


def _coerce_positive_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None
