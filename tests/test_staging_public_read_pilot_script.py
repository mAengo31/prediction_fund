from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_staging_public_read_pilot_builds_targeted_payload(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    record_path = tmp_path / "collection_payload.json"
    curl_path = fake_bin / "curl"
    curl_path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
outfile = Path(args[args.index("-o") + 1])
joined = " ".join(args)
data = args[args.index("-d") + 1] if "-d" in args else None
if data and "/api/v1/dataops/collection/run-once" in joined:
    Path(os.environ["CURL_RECORD"]).write_text(data)
if outfile.name == "collection_run.json":
    payload = {"run": {"collection_run_id": "collection_run_test"}}
elif outfile.name == "collection_run_detail.json":
    payload = {
        "collection_run_id": "collection_run_test",
        "status": "COMPLETED",
        "venue_names": ["kalshi"],
        "payloads_archived": 1,
        "markets_processed": 1,
        "errors_count": 0,
    }
elif outfile.name == "coverage_compute.json":
    payload = {"coverage_score": 100}
else:
    payload = []
outfile.write_text(json.dumps(payload))
""",
        encoding="utf-8",
    )
    curl_path.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "API_BASE_URL": "https://staging.example.test",
        "PREDICTION_DESK_API_TOKEN": "redacted-test-token",
        "CONFIRM_PUBLIC_READ_ONLY": "true",
        "PUBLIC_READ_VENUES": "kalshi",
        "PUBLIC_READ_ENDPOINT_TYPES": "MARKET_DETAIL,ORDERBOOK",
        "PUBLIC_READ_MARKET_IDS": "kalshi_market_example",
        "MAX_PAYLOADS": "5",
        "CURL_RECORD": str(record_path),
    }
    result = subprocess.run(
        ["scripts/staging_public_read_pilot.sh"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "MANUAL_PUBLIC_FETCH"
    assert payload["allow_network"] is True
    assert payload["venue_names"] == ["kalshi"]
    assert payload["endpoint_types"] == ["MARKET_DETAIL", "ORDERBOOK"]
    assert payload["market_ids"] == ["kalshi_market_example"]
    assert payload["max_payloads"] == 5
