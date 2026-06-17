from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import PreTradeAction
from prediction_desk.pretrade.service import PreTradeService

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
MARKET_ID = "mkt_cpi_yoy_at_least_3pct_2026_09"


def test_default_policy_creation_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "policy.db")
    with repo as current:
        service = PreTradeService(current)
        first = service.create_default_pretrade_policy_if_missing()
        second = service.create_default_pretrade_policy_if_missing()

    assert first.policy_id == second.policy_id
    assert first.policy_name == "default_pretrade_policy"


def test_service_persists_input_snapshot_and_decision(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "service_persist.db")
    with repo as current:
        result = PreTradeService(current).check_market_default_intent(MARKET_ID, ASOF)
        stored = current.get_pretrade_decision(result.decision.pretrade_decision_id)

    assert stored is not None
    assert stored.input_snapshot_id == result.input_snapshot.input_snapshot_id
    assert result.input_snapshot.input_hash


def test_service_tolerates_duplicate_checks_deterministically(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "service_duplicate.db")
    with repo as current:
        service = PreTradeService(current)
        first = service.check_market_default_intent(MARKET_ID, ASOF)
        second = service.check_market_default_intent(MARKET_ID, ASOF)

    assert first.decision.pretrade_decision_id == second.decision.pretrade_decision_id
    assert first.input_snapshot.input_hash == second.input_snapshot.input_hash


def test_future_pretrade_decision_not_returned_by_asof_lookup(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "service_future.db")
    with repo as current:
        result = PreTradeService(current).check_market_default_intent(MARKET_ID, ASOF)
        future = result.decision.model_copy(
            update={
                "pretrade_decision_id": "future_pretrade_decision",
                "asof_timestamp": ASOF + timedelta(days=1),
                "available_at": ASOF + timedelta(days=1),
                "output_hash": "future_output_hash",
                "action": PreTradeAction.NO_TRADE,
            }
        )
        current.save_pretrade_decision(future)
        latest = current.get_latest_pretrade_decision_asof(
            MARKET_ID,
            ASOF + timedelta(hours=1),
        )

    assert latest is not None
    assert latest.pretrade_decision_id == result.decision.pretrade_decision_id


class _RepoContext:
    def __init__(self, database_path: Path) -> None:
        self.database_url = f"sqlite:///{database_path}"
        init_db(self.database_url)
        engine = build_engine(self.database_url)
        self.session_factory = build_session_factory(engine)

    def __enter__(self) -> PredictionMarketRepository:
        self.context = self.session_factory.begin()
        session = self.context.__enter__()
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        return repo

    def __exit__(self, *exc: object) -> None:
        self.context.__exit__(*exc)


def _repo(database_path: Path) -> _RepoContext:
    return _RepoContext(database_path)
