"""Example fixtures used by the local CLI and tests."""

from prediction_desk.examples.sample_markets import (
    SampleMarketBundle,
    load_sample_data,
    sample_markets,
)

__all__ = ["SampleMarketBundle", "load_sample_data", "sample_markets"]
