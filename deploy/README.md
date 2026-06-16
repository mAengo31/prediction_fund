# Deployment Templates

These files are safe deployment templates for the internal `prediction-desk` research API.
They intentionally contain no exchange credentials, no private keys, no wallet material, and
no trading secrets.

## Local Docker Compose

Use Docker Compose for local end-to-end Postgres validation:

```bash
cp .env.example .env
docker compose build
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm app prediction-desk load-sample-data
docker compose up -d app
curl http://localhost:8000/healthz
curl http://localhost:8000/api/v1/markets
```

Or run the deterministic smoke path:

```bash
scripts/smoke_docker.sh
```

## Staging Render-Style Deployment

`deploy/render.yaml` is a template for a low-friction staging deployment:

- Web service runs the Docker image.
- Managed Postgres is referenced through `DATABASE_URL`.
- `PREDICTION_DESK_API_TOKEN` is marked as a secret placeholder.
- `REQUIRE_API_TOKEN=true`.
- `ENABLE_OPENAPI_DOCS=false`.

Run migrations as an explicit release/manual command:

```bash
scripts/migrate.sh
```

Do not configure venue credentials in staging for this project stage.

## Production Research Target

The intended production research shape is:

- AWS ECS/Fargate for the API container.
- RDS Postgres.
- AWS Secrets Manager for API token and database credentials.
- Private networking/VPC.
- Internal load balancer or private endpoint.
- Centralized logs and metrics.

Bearer-token auth is a temporary staging mechanism. Replace it with SSO, service-to-service
auth, or another managed identity boundary before production research use.

## Access Model

- Local: localhost only.
- Staging: token-protected HTTPS endpoint.
- Production research: private/internal endpoint over VPN, SSO, or private networking.
- Future UI clients should call this API and should not bypass it with direct database access.

## What Remains Private

Keep these out of the repository and out of images:

- API tokens.
- Database passwords.
- Cloud credentials.
- Exchange credentials.
- Wallet keys or seed material.
- Private signing keys.

## Non-Trading Boundary

This service is not an execution service. It exposes stored canonical data and deterministic
trust-verdict recomputation. It must not place orders, create wallets, hold keys, or call
venue trading APIs.
