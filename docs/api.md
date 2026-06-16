# prediction-desk API

The `prediction-desk` API is an internal research API. It exposes stored prediction-market
artifacts and deterministic trust-verdict scoring. It does not trade, place orders, connect
to venues, or call external APIs.

## Authentication

Authentication is controlled by runtime config:

- `REQUIRE_API_TOKEN=false`: bearer-token checks are skipped.
- `REQUIRE_API_TOKEN=true`: protected endpoints require
  `Authorization: Bearer <PREDICTION_DESK_API_TOKEN>`.
- `/healthz` is always public.
- `/readyz` follows the same token requirement as other protected endpoints.

Do not put real tokens in source control, Docker images, or Compose files.

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/healthz` | Public | Process liveness check. Does not touch the database. |
| `GET` | `/readyz` | Configurable | Database readiness check using `SELECT 1`. |
| `GET` | `/version` | Configurable | Service version, commit, and environment. |
| `GET` | `/markets` | Configurable | Compact market list with optional filters. |
| `GET` | `/markets/{market_id}` | Configurable | Full stored market object. |
| `GET` | `/markets/{market_id}/rule-snapshots/latest` | Configurable | Latest stored rule snapshot. |
| `GET` | `/markets/{market_id}/trust-verdicts/latest` | Configurable | Latest stored trust verdict. |
| `POST` | `/markets/{market_id}/trust-verdicts/recompute` | Configurable | Recompute and store a deterministic trust verdict from stored snapshots. |

## Local Examples

Start the API locally:

```bash
prediction-desk init-db
prediction-desk load-sample-data
scripts/run_api.sh
```

Health:

```bash
curl http://localhost:8000/healthz
```

Readiness:

```bash
curl http://localhost:8000/readyz
```

List markets:

```bash
curl "http://localhost:8000/markets?limit=100&offset=0"
```

Filter markets:

```bash
curl "http://localhost:8000/markets?status=ACTIVE&venue_id=sample_research_venue"
```

Get one market:

```bash
curl http://localhost:8000/markets/mkt_sfo_rain_2026_09_01
```

Recompute a trust verdict:

```bash
curl -X POST \
  http://localhost:8000/markets/mkt_sfo_rain_2026_09_01/trust-verdicts/recompute
```

With token auth enabled:

```bash
curl -H "Authorization: Bearer local-dev-token" http://localhost:8000/version
```

The recompute endpoint reads the stored market, latest rule snapshot, and latest order book
snapshot. It does not fetch venue data, place orders, or create any trading instruction.
