#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "API_BASE_URL is required; staging desk cycle was not run." >&2
  exit 1
fi

python - <<'PY'
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib import error, parse, request

api_base_url = os.environ["API_BASE_URL"].rstrip("/")
api_token = os.environ.get("PREDICTION_DESK_API_TOKEN")
headers = {"Content-Type": "application/json"}
if api_token:
    headers["Authorization"] = f"Bearer {api_token}"


def api_call(method: str, path: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = request.Request(api_base_url + path, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=90) as response:
        body = response.read()
        return json.loads(body) if body else None


def optional_call(name: str, method: str, path: str, payload: dict | None = None):
    try:
        result = api_call(method, path, payload)
        print(f"ok {name}")
        return result
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        print(f"skip {name}: HTTP {exc.code} {detail}")
    except Exception as exc:  # noqa: BLE001 - staging script should continue optional steps.
        print(f"skip {name}: {type(exc).__name__}: {exc}")
    return None


def quote(value: str) -> str:
    return parse.quote(value, safe="")


def decimalish(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def compact_title(title: str | None) -> str | None:
    if title is None:
        return None
    return title if len(title) <= 120 else title[:117] + "..."


def choose_paper_candidate(markets: list[dict]) -> tuple[str, str] | None:
    for market in markets:
        market_id = market["market_id"]
        latest = optional_call(
            f"market-data latest {market_id}",
            "GET",
            f"/api/v1/markets/{quote(market_id)}/market-data/latest",
        )
        if not latest:
            continue
        price = latest.get("price_snapshot") or {}
        liquidity = latest.get("liquidity_snapshot") or {}
        candidate_price = (
            decimalish(price.get("ask"))
            or decimalish(liquidity.get("best_ask"))
            or decimalish(price.get("price"))
            or decimalish(price.get("mid"))
        )
        if candidate_price is not None and Decimal("0") < candidate_price < Decimal("1"):
            return market_id, format(candidate_price, "f")
    return None


def main() -> int:
    asof = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")

    health = api_call("GET", "/healthz")
    ready = api_call("GET", "/readyz")
    markets = api_call("GET", "/api/v1/markets")
    market_ids = [market["market_id"] for market in markets]
    market_titles = {market["market_id"]: market.get("title") for market in markets}
    print(f"health={health.get('status')} ready={ready.get('status')} markets={len(markets)}")
    if not market_ids:
        print("no markets available; stopping desk cycle")
        return 0

    coverage = api_call("POST", "/api/v1/dataops/coverage/compute", {"scope_type": "GLOBAL"})
    gaps = api_call(
        "POST",
        "/api/v1/dataops/gaps/detect",
        {"scope_type": "GLOBAL", "expected_cadence_seconds": 3600},
    )
    gap_counts = Counter(gap.get("gap_type") for gap in gaps)
    print(
        "coverage "
        f"score={coverage.get('coverage_score')} "
        f"gaps={json.dumps(dict(sorted(gap_counts.items())), sort_keys=True)}"
    )

    integrity = optional_call(
        "integrity analyze",
        "POST",
        "/api/v1/integrity/analyze",
        {
            "market_ids": market_ids,
            "asof_timestamp": asof,
            "force": False,
            "thresholds": {},
            "metadata": {"source": "staging_desk_cycle"},
        },
    ) or []
    print(f"integrity_assessments={len(integrity)}")

    equivalence = optional_call(
        "equivalence run",
        "POST",
        "/api/v1/equivalence/runs",
        {
            "name": "staging desk cycle equivalence",
            "asof_timestamp": asof,
            "market_ids": market_ids,
            "min_candidate_score": 40,
            "max_pairs": 25,
            "build_classes": True,
            "force": False,
            "metadata": {"source": "staging_desk_cycle"},
        },
    )
    equivalence_assessments = (equivalence or {}).get("assessments", [])
    print(f"equivalence_assessments={len(equivalence_assessments)}")

    divergence = None
    if equivalence_assessments:
        divergence = optional_call(
            "divergence run",
            "POST",
            "/api/v1/divergence/runs",
            {
                "name": "staging desk cycle divergence",
                "asof_timestamp": asof,
                "equivalence_assessment_ids": [
                    item["equivalence_assessment_id"] for item in equivalence_assessments
                ],
                "max_pairs": 25,
                "force": False,
                "config": {},
                "metadata": {"source": "staging_desk_cycle"},
            },
        )
    else:
        print("skip divergence run: no equivalence assessments")
    divergence_assessments = (divergence or {}).get("summary", {}).get("total_assessments", 0)
    print(f"divergence_assessments={divergence_assessments}")

    optional_call("default pretrade policy", "POST", "/api/v1/pretrade/policies/default", {})
    pretrade = optional_call(
        "pretrade run",
        "POST",
        "/api/v1/pretrade/runs",
        {
            "name": "staging desk cycle pretrade",
            "asof_timestamp": asof,
            "market_ids": market_ids,
            "max_checks": len(market_ids),
            "default_requested_size_units": "1",
            "strategy_context": "RESEARCH",
            "intent_type": "RESEARCH_ONLY",
            "metadata": {"source": "staging_desk_cycle"},
        },
    )
    pretrade_decisions = (pretrade or {}).get("summary", {}).get("total_decisions", 0)
    print(f"pretrade_decisions={pretrade_decisions}")

    optional_call("default paper policy", "POST", "/api/v1/paper/policies/default", {})
    paper_orders = 0
    paper_fills = 0
    paper_candidate = choose_paper_candidate(markets)
    if paper_candidate:
        market_id, requested_price = paper_candidate
        paper = optional_call(
            "paper simulate intent",
            "POST",
            "/api/v1/paper/simulate-intent",
            {
                "market_id": market_id,
                "strategy_context": "RESEARCH",
                "side": "BUY",
                "intent_type": "AGGRESSIVE_LIMIT",
                "requested_price": requested_price,
                "requested_size_units": "1",
                "asof_timestamp": asof,
                "metadata": {"source": "staging_desk_cycle"},
            },
        )
        if paper:
            paper_orders = 1 if paper.get("order") else 0
            paper_fills = len(paper.get("fills", []))
    else:
        print("skip paper simulate intent: no eligible market-data price")
    print(f"paper_orders_created={paper_orders} paper_fills_created={paper_fills}")

    strategies = optional_call(
        "default research strategies",
        "POST",
        "/api/v1/research/strategies/default",
        {},
    ) or []
    baseline_strategy_ids = [
        strategy["strategy_id"]
        for strategy in strategies
        if strategy.get("strategy_name") == "baseline_research_only_v1"
    ]
    research = optional_call(
        "research run",
        "POST",
        "/api/v1/research/runs",
        {
            "name": "staging desk cycle research",
            "start_time": asof,
            "end_time": asof,
            "interval_seconds": 3600,
            "strategy_ids": baseline_strategy_ids or None,
            "market_ids": market_ids,
            "max_steps": 25,
            "max_proposals": 25,
            "enable_paper_simulation": False,
            "initial_cash_simulated": "1000",
            "force": False,
            "metadata": {"source": "staging_desk_cycle"},
        },
    )
    research_summary = (research or {}).get("summary", {})
    print(
        "research "
        f"signals={research_summary.get('total_signals', 0)} "
        f"proposals={research_summary.get('total_proposals', 0)} "
        f"traces={research_summary.get('total_pretrade_checks', 0)} "
        f"run_id={(research or {}).get('run', {}).get('research_run_id')}"
    )

    queue_items = api_call(
        "POST",
        "/api/v1/workbench/queues/build",
        {
            "asof_timestamp": asof,
            "market_ids": market_ids,
            "queue_name": "staging_desk_cycle",
            "limit": 500,
            "force": False,
        },
    )
    priority_counts = Counter(item.get("priority_bucket") for item in queue_items)
    reason_counts: Counter[str] = Counter()
    for item in queue_items:
        reason_counts.update(item.get("reason_codes") or [])
    print(
        "workbench_queue "
        f"items={len(queue_items)} "
        f"priority_counts={json.dumps(dict(sorted(priority_counts.items())), sort_keys=True)} "
        f"top_reasons={json.dumps(dict(reason_counts.most_common(10)), sort_keys=True)}"
    )

    top_items = sorted(queue_items, key=lambda item: (-item["priority_score"], item["market_id"]))[:5]
    print("top_queue_items")
    for item in top_items:
        print(
            json.dumps(
                {
                    "market_id": item["market_id"],
                    "title": compact_title(market_titles.get(item["market_id"])),
                    "priority_score": item["priority_score"],
                    "priority_bucket": item["priority_bucket"],
                    "primary_reason_code": item["primary_reason_code"],
                    "reason_codes": item.get("reason_codes", [])[:8],
                },
                sort_keys=True,
            )
        )
        optional_call(
            f"decision card {item['market_id']}",
            "POST",
            f"/api/v1/workbench/markets/{quote(item['market_id'])}/decision-card",
            {"asof_timestamp": asof, "force": False},
        )

    note = api_call(
        "POST",
        "/api/v1/workbench/notes",
        {
            "market_id": top_items[0]["market_id"] if top_items else market_ids[0],
            "author": "staging-desk-cycle",
            "note_type": "OBSERVATION",
            "text": "Staging desk cycle completed. No trading action.",
            "tags": ["staging", "desk-cycle", "validation"],
            "metadata": {"source": "staging_desk_cycle"},
        },
    )
    print(f"desk_note_id={note['note_id']}")
    print("staging_desk_cycle ok")
    return 0


raise SystemExit(main())
PY
