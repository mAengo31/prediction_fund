from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from prediction_desk.research.strategies import default_research_strategy_definitions
from tests.research_helpers import ASOF, research_proposal


def test_default_research_strategies_created_deterministically() -> None:
    first = default_research_strategy_definitions(created_at=ASOF)
    second = default_research_strategy_definitions(created_at=ASOF)

    assert [definition.strategy_id for definition in first] == [
        definition.strategy_id for definition in second
    ]
    assert [definition.strategy_name for definition in first] == [
        "baseline_research_only_v1",
        "trust_verdict_allow_filter_v1",
        "integrity_pass_filter_v1",
        "divergence_research_hypothesis_v1",
        "composite_conservative_research_v1",
    ]
    assert all(definition.requires_pretrade for definition in first)


def test_research_proposal_validates_size_and_probability_price() -> None:
    with pytest.raises(ValidationError):
        research_proposal(requested_size_units=Decimal("0"))

    with pytest.raises(ValidationError):
        research_proposal(requested_price=Decimal("1.01"))

