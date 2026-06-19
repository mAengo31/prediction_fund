# Vendor Data Evaluation

Vendor Dataset Intake + Evaluation Scaffold v1 is a neutral way to evaluate local
historical-data samples from third-party providers before deciding whether a fuller
integration is worth building.

It is not a vendor integration. It does not call vendor APIs, accept vendor credentials,
pull external URLs, create execution adapters, place orders, route orders, or mutate
canonical market data. V1 works from local sample files only and produces persisted
inspection, validation, dry-run, and evaluation artifacts.

## Why Evaluate Vendor Data

Third-party historical data can help fill replay and research coverage gaps, but raw data
is not the moat. The durable value in prediction-desk is canonical processing, point-in-
time replay safety, trust scoring, pre-trade gating, simulated paper execution, coverage
measurement, and desk workbench review.

The vendor scaffold answers practical pre-purchase questions:

- Are market, condition, question, Gamma, and token identifiers present?
- Are CLOB token or asset IDs usable for Polymarket mapping?
- Are timestamps parseable and replay-safe?
- Is orderbook and price-history data shaped enough for canonical import later?
- Are sample rows duplicate-prone or missing required fields?
- What should we ask the vendor before buying or integrating?

## Core Objects

`VendorDatasetSource` records a candidate vendor/dataset/version, contact URL, license
readiness, supported file types, and metadata.

`VendorSampleFile` records a local sample file: name, type, absolute local path, size,
deterministic hash, row count, and schema summary. The original file is not mutated. V1
archives metadata and hashes, not a separate file copy.

`VendorSchemaInspection` records detected columns, simple detected types, likely
timestamp columns, market identifiers, token identifiers, price/size columns, orderbook
columns, trade columns, resolution columns, and warnings.

`VendorDataValidationReport` records row-level validation status and grouped issues:
missing columns, token mapping issues, timestamp issues, price issues, duplicate issues,
point-in-time warnings, and general warnings.

`VendorImportDryRun` estimates canonical objects that could be created later. It counts
candidate markets, token mappings, orderbook snapshots, price snapshots, trade prints,
and resolution events. It does not persist canonical market data.

`VendorEvaluationReport` combines inspection, validation, and dry-run results into
scores for coverage, token mapping, timestamp quality, orderbook quality, price history,
replay safety, and license readiness. It also stores strengths, weaknesses, questions
for the vendor, and a buy/hold/reject-oriented recommendation.

## Supported Files

V1 accepts local paths only:

- CSV
- JSON
- JSONL
- Parquet only when an appropriate local optional reader is available

URLs are rejected. Files above the configured maximum size are rejected. The default
limit is 100 MB.

## Schema Inspection

The inspector detects likely fields by name. It looks for market identifiers such as
`market_id`, `condition_id`, `question_id`, `gamma_market_id`, `slug`, `event_id`, and
`market_address`.

It detects token identifiers such as `clob_token_id`, `token_id`, `asset_id`,
`yes_token_id`, and `no_token_id`.

It also identifies likely orderbook, trade, price-history, timestamp, and resolution
columns. Detection is heuristic: it helps triage a sample, but it is not a production
import contract.

## Validation Checks

Validation checks include:

- timestamp parseability
- timezone-awareness warnings
- probability-style price values in `[0, 1]`
- nonnegative size/quantity fields
- token IDs when token-level samples need them
- condition IDs when market mapping depends on them
- duplicate likely row keys
- presence or absence of `observed_at`, `captured_at`, and `available_at`
- orderbook row shape with side/price/size or equivalent columns
- resolution fields when the sample claims resolved-market history

Missing fields are reported. The system does not fabricate token IDs, timestamps,
orderbooks, or resolution events.

## Dry-Run Import

Dry-run import is intentionally non-mutating. It estimates what a future canonical import
could do:

- would create markets
- would create token mappings
- would create price snapshots
- would create orderbook snapshots
- would create trade prints, if a trade import model is introduced
- would create resolution events, when resolvable
- would skip rows with missing identifiers
- would fail rows with invalid timestamps or prices

V1 does not overwrite or backfill canonical market data from vendor samples.

## CLI

```bash
prediction-desk vendor-register-source \
  --vendor-name "SampleVendor" \
  --dataset-name "Polymarket CLOB history" \
  --dataset-version sample-v1 \
  --license-status SAMPLE_ONLY

prediction-desk vendor-load-sample \
  --vendor-source-id vendor_source_... \
  --file-path sample_data/vendor_samples/polymarket_orderbook_sample.jsonl

prediction-desk vendor-inspect-sample --sample-file-id vendor_sample_...
prediction-desk vendor-validate-sample --sample-file-id vendor_sample_...
prediction-desk vendor-dry-run-import \
  --sample-file-id vendor_sample_... \
  --sample-kind orderbook
prediction-desk vendor-evaluate \
  --vendor-source-id vendor_source_... \
  --sample-file-id vendor_sample_...
prediction-desk vendor-reports --vendor-source-id vendor_source_...
```

## API

Vendor routes live under `/api/v1/vendor-data`:

- `POST /vendor-data/sources`
- `GET /vendor-data/sources`
- `GET /vendor-data/sources/{vendor_source_id}`
- `POST /vendor-data/samples/load`
- `GET /vendor-data/samples`
- `GET /vendor-data/samples/{sample_file_id}`
- `POST /vendor-data/samples/{sample_file_id}/inspect`
- `POST /vendor-data/samples/{sample_file_id}/validate`
- `POST /vendor-data/samples/{sample_file_id}/dry-run-import`
- `POST /vendor-data/evaluate`
- `GET /vendor-data/reports`
- `GET /vendor-data/reports/{evaluation_report_id}`

These endpoints use the existing bearer-token protection and local file paths only. They
do not import URLs or call vendor APIs.

## Sample Files

Synthetic samples live in `sample_data/vendor_samples/`:

- `polymarket_price_history_sample.csv`
- `polymarket_orderbook_sample.jsonl`
- `polymarket_trades_sample.csv`
- `bad_missing_token_sample.csv`

The bad sample exists to verify rejection and warning paths.

## Decision Use

Evaluation reports should guide vendor outreach and sample requests. A promising sample
still needs license clarification, replay-safety confirmation, identifier mapping review,
and a later production importer design before any canonical data import is allowed.

This scaffold supports a `vendor outreach / sample import / production import later /
hold` decision. It does not enable live trading, public-read scheduling, vendor API
pulls, wallets, private keys, venue credentials, or order routing.
