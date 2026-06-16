#!/usr/bin/env bash
set -euo pipefail

uvicorn prediction_desk.api.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
