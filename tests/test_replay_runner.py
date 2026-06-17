from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.runner import compute_input_hash, compute_output_hash, run_replay


def test_replay_run_uses_rule_snapshot_asof_before_and_after_change(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay_runner.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = run_replay(
            ReplayRunConfig(
                name="rule change replay",
                policy_name="trust_verdict_v1",
                start_time=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                end_time=datetime(2026, 6, 17, 12, 0, tzinfo=UTC),
                interval_seconds=86400,
                market_ids=["mkt_rate_cut_rule_change_2026"],
                max_steps=10,
            ),
            repo,
        )

    assert [step.rule_snapshot_id for step in result.steps] == [
        "rule_rate_cut_rule_change_2026_v1",
        "rule_rate_cut_rule_change_2026_v2",
    ]
    assert result.summary.total_steps == 2
    assert result.summary.markets_replayed == 1


def test_replay_generated_trust_verdict_uses_replay_timestamp(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay_runner.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    replay_timestamp = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = run_replay(
            ReplayRunConfig(
                policy_name="trust_verdict_v1",
                start_time=replay_timestamp,
                end_time=replay_timestamp.replace(hour=14),
                interval_seconds=3600,
                market_ids=["mkt_cpi_yoy_at_least_3pct_2026_09"],
                max_steps=10,
                force_recompute_verdicts=True,
            ),
            repo,
        )
        verdict = repo.get_latest_trust_verdict_asof(
            "mkt_cpi_yoy_at_least_3pct_2026_09",
            replay_timestamp,
        )

    assert result.steps[0].asof_timestamp == replay_timestamp
    assert verdict is not None
    assert verdict.asof_timestamp.replace(tzinfo=UTC) == replay_timestamp


def test_replay_hashes_are_deterministic() -> None:
    input_payload = {
        "market_id": "mkt",
        "asof_timestamp": "2026-06-16T12:00:00+00:00",
        "rule_snapshot_id": "rule",
    }
    output_payload_a = {
        "action": "ALLOW",
        "allowed_size_multiplier": "1.0",
        "reason_codes": ["B", "A"],
    }
    output_payload_b = {
        "action": "ALLOW",
        "allowed_size_multiplier": "1.0",
        "reason_codes": ["A", "B"],
    }

    assert compute_input_hash(input_payload) == compute_input_hash(dict(input_payload))
    assert compute_output_hash(output_payload_a) == compute_output_hash(output_payload_b)


def test_replay_run_persists_steps_and_summary(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay_runner.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = run_replay(
            ReplayRunConfig(
                policy_name="allow_all_v1",
                start_time=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                end_time=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
                interval_seconds=3600,
                market_ids=["mkt_cpi_yoy_at_least_3pct_2026_09"],
                max_steps=10,
            ),
            repo,
        )
        persisted_steps = repo.list_replay_steps(result.run.run_id)
        persisted_summary = repo.get_replay_summary(result.run.run_id)

    assert len(persisted_steps) == 2
    assert persisted_summary is not None
    assert persisted_summary.total_steps == 2
