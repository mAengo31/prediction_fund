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

Timestamp detection recognizes strong timestamp names and aliases such as `timestamp`,
`ts`, `time`, `datetime`, `date_time`, `created_time`, `created_at`, `observed_at`,
`captured_at`, `available_at`, and `unix_timestamp`. Numeric Unix epoch values are
accepted only after a column has been identified as timestamp-like by name; arbitrary
numeric columns are not treated as timestamps just because their values look numeric.

## Schema Mapping Configs

Some vendor files use dataset-specific column names that should not become global
heuristics. V1 supports optional local JSON mapping configs for inspection, validation,
dry-run import, and evaluation. Mapping files are local-only, must not contain secrets,
and do not enable canonical writes.

Mapping configs can identify market, condition, question, Gamma, slug, token, and asset
ID columns; observed/captured/available timestamp columns; market start and elapsed-time
columns; price and top-of-book quote columns; orderbook depth columns; trade evidence
columns; resolution columns; and feature columns that should be preserved as sample
metadata context.

```bash
prediction-desk vendor-inspect-sample \
  --sample-file-id vendor_sample_... \
  --mapping-config sample_data/vendor_samples/mapping_configs/debayan31415_btc_5m_top_of_book.json

prediction-desk vendor-validate-sample \
  --sample-file-id vendor_sample_... \
  --mapping-config sample_data/vendor_samples/mapping_configs/debayan31415_btc_5m_top_of_book.json

prediction-desk vendor-dry-run-import \
  --sample-file-id vendor_sample_... \
  --mapping-config sample_data/vendor_samples/mapping_configs/debayan31415_btc_5m_top_of_book.json

prediction-desk vendor-evaluate \
  --vendor-source-id vendor_source_... \
  --sample-file-id vendor_sample_... \
  --mapping-config sample_data/vendor_samples/mapping_configs/debayan31415_btc_5m_top_of_book.json
```

The bundled BTC mapping declares `bid_YES`, `ask_YES`, `bid_NO`, and `ask_NO` as binary
top-of-book quote fields. Top-of-book quotes are not full L2 depth, so mapped dry-run
counts can increase price/top-of-book snapshot estimates without counting orderbook
depth. If token or asset columns are absent, token mappings remain zero and token-mapping
warnings remain valid.

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

## Large-File Sampling

Large vendor files should be sampled before inspection or dry-run evaluation. The loader
supports `max_rows` on sample load, inspection, validation, and dry-run import. CSV and
JSONL files stream the first N rows. Parquet files use PyArrow batch reads when available
so a bounded row sample can be read without loading the whole file into memory.

Files larger than 500 MB require row sampling before local processing. Sample metadata
records `sampled_row_count`, `total_row_count` when cheaply available, and
`sample_limit_applied`. The original vendor file is not mutated, and sampled evaluation
does not write canonical market data.

Dry-run classification is conservative:

- price history rows can count price snapshots when timestamp and probability-style price
  evidence is present
- orderbook rows can count orderbook snapshots only with book-specific evidence such as
  bid/ask fields, level/depth fields, or token + side + price + size when the sample is
  explicitly marked as `orderbook`
- trade rows can count trade prints only with trade-specific evidence such as `trade_id`,
  `transaction_hash`, maker/taker fields, order IDs, fill indicators, or execution
  timestamps
- price + size alone does not imply a trade
- trade rows do not imply orderbook depth
- `sample_kind` guides classification but does not override missing evidence

Ambiguous rows are warned and under-counted rather than over-counted. Dry-run warning
codes include `SUPPRESSED_TRADE_COUNT_MISSING_TRADE_EVIDENCE`,
`SUPPRESSED_ORDERBOOK_COUNT_MISSING_BOOK_EVIDENCE`, `AMBIGUOUS_PRICE_SIZE_ROWS`, and
`SAMPLE_KIND_SCHEMA_MISMATCH`.

For `BINARY_TOP_OF_BOOK_QUOTES`, mapped YES/NO bid/ask fields can produce dry-run
`price_snapshots` and `top_of_book_quote_snapshots`. They do not produce token mappings,
trade prints, or full orderbook snapshots unless the sample also provides token/asset,
trade, or depth evidence.

## CLI

```bash
prediction-desk vendor-register-source \
  --vendor-name "SampleVendor" \
  --dataset-name "Polymarket CLOB history" \
  --dataset-version sample-v1 \
  --license-status SAMPLE_ONLY

prediction-desk vendor-load-sample \
  --vendor-source-id vendor_source_... \
  --file-path sample_data/vendor_samples/polymarket_orderbook_sample.jsonl \
  --max-rows 10000

prediction-desk vendor-inspect-sample --sample-file-id vendor_sample_... --max-rows 10000
prediction-desk vendor-validate-sample --sample-file-id vendor_sample_... --max-rows 10000
prediction-desk vendor-dry-run-import \
  --sample-file-id vendor_sample_... \
  --sample-kind orderbook \
  --max-rows 10000
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

## Local Kaggle Sample Findings

The first local Kaggle sample evaluated was
`luciferforge/polymarket-historical-prices`. It contains `markets.csv` and
`prices_sample.csv`. After timestamp alias hardening, `prices_sample.csv` detects `ts`
as a timestamp and dry-run can count price snapshots. The sample still remains weak for
replay planning because it lacks CLOB token IDs or asset IDs, has unclear market ID
semantics, and does not provide separate `observed_at`, `captured_at`, and
`available_at` fields.

The second local Kaggle sample evaluated was
`debayan31415/polymarket-5-minutes-btc-up-down-data`. It contains a high-frequency BTC
5-minute market CSV with `slug`, Unix-style `start_time`, YES/NO bid/ask quote fields,
and resolution columns.

Without a mapping config, inspection detects `start_time` and `resolved`, but not
`ask_YES`, `bid_YES`, `ask_NO`, or `bid_NO` as price/quote fields. The dry-run result is
mostly markets-only and the evaluation remains `HOLD`.

With `sample_data/vendor_samples/mapping_configs/debayan31415_btc_5m_top_of_book.json`,
inspection recognizes the YES/NO quote fields and `winner`. The mapped dry-run over the
113,245-row local file detected:

- 1,191 markets
- 113,245 dry-run price snapshots
- 113,245 dry-run top-of-book quote snapshots
- 1,191 dry-run resolution events
- 0 token mappings
- 0 full orderbook snapshots
- 0 trade prints

The mapped evaluation remains `HOLD`: coverage improves from 40 to 60, but token mapping
stays at 30, full orderbook depth is still absent, and replay safety still depends on
clarifying `observed_at`, `captured_at`, and `available_at`. Mapped validation also found
crossed YES/NO quote pairs, which should be clarified with the dataset owner before using
the sample for research beyond dry-run evaluation.

The next L2 candidate checked was
`ithiria137/polymarket-l2-capture-cumulative-2026`. Its useful files are SQLite
databases of approximately 1.36 GB and 1.97 GB, and the total dataset is over 2 GB. The
dataset was not downloaded because the current scaffold does not sample SQLite files and
the task guardrail blocks full large-dataset download without confirmation.

The backup L2 candidate checked was
`marvingozo/polymarket-tick-level-orderbook-dataset`. The full orderbook parquet files
are large, but the dataset includes smaller snapshot parquet files. The evaluated bounded
sample used `snapshots/snapshots_2026-03-23.parquet`:

- file size: 66,369,237 bytes
- total rows from Parquet metadata: 581,371
- sampled rows loaded: 10,000
- detected market IDs: `market_id`, `data_market_id`
- detected token IDs: `data_token_id`
- detected timestamps: `data_timestamp`, `timestamp_created_at`, `timestamp_received`
- detected orderbook evidence: `data_bids`, `data_asks`, `data_best_bid`, `data_best_ask`,
  `data_side`

The sampled dry-run detected 3,549 markets, 3,549 token mappings, 9,886 orderbook
snapshots, and 9,886 price snapshots. It did not count trades or resolution events. The
sampled evaluation was `PROMISING`, with strong token, timestamp, orderbook, and price
scores. The remaining caveats are license readiness (`CC BY-NC 4.0` is not commercial
approval), point-in-time semantics for received/created timestamps, and the fact that
sampled evaluation is not a full-dataset acceptance test.

## Azure Staging Validation

Azure staging validation for v1 used the synthetic samples packaged in the container
image, not external vendor APIs. The staging API was deployed as
`prediction-desk:f89c5ca`, and Azure Postgres was migrated through `20260619_0016`.

The validated synthetic source was:

`vendor_source_synthetic_polymarket_vendor_sample_eval_v1_dd348c45279c7128`

The three good samples produced a `PROMISING` evaluation report with usable token/asset
identifiers, orderbook-like rows, probability-style price history, and replay-safe
timestamp fields. The report including `bad_missing_token_sample.csv` produced
`NEEDS_CLARIFICATION`, with missing token identifiers, out-of-range prices, unparseable
timestamps, and point-in-time questions.

The dry-run path produced vendor artifacts only:

- vendor dataset sources
- vendor sample files
- schema inspections
- validation reports
- import dry runs
- evaluation reports

It did not create canonical markets, orderbooks, price snapshots, liquidity snapshots, or
quality reports from vendor sample rows.

## Decision Use

Evaluation reports should guide vendor outreach and sample requests. A promising sample
still needs license clarification, replay-safety confirmation, identifier mapping review,
and a later production importer design before any canonical data import is allowed.

This scaffold supports a `vendor outreach / sample import / production import later /
hold` decision. It does not enable live trading, public-read scheduling, vendor API
pulls, wallets, private keys, venue credentials, or order routing.
