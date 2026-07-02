"""
Strategy configuration — tunable knobs for ingestion and cross-venue matching.
Edit these to change which markets we track and how we match them.
"""


class StrategyConfig:
    # ------------------------------------------------------------------
    # Kalshi — which series to ingest (2026 midterms)
    # ------------------------------------------------------------------
    KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

    KALSHI_SERIES: list[str] = [
        # Senate races — verified live against Kalshi API 2026-07-01
        "SENATEOK", "SENATEAL", "SENATERI", "SENATEAK", "SENATEMS",
        "SENATEPA", "SENATECT", "SENATEMD", "SENATEMA", "SENATEWA",
        "SENATEOHS", "SENATEUT", "SENATEMT", "SENATEAR", "SENATEIL",
        "SENATEND", "SENATENH", "SENATEMN", "SENATENM", "SENATECO",
        "SENATEOR", "SENATEMI", "SENATEWV", "SENATEDE", "SENATEVT",
        # Governor races
        "GOVPARTYFL", "GOVPARTYGA", "GOVPARTYSC", "GOVPARTYOR",
        "GOVPARTYIA", "GOVPARTYME", "GOVPARTYMA", "GOVPARTYMT",
        "GOVPARTYMD", "GOVPARTYMI", "GOVPARTYTX", "GOVPARTYNY",
        "GOVPARTYCA", "GOVPARTYNC", "GOVPARTYNH", "GOVPARTYNM",
        "GOVPARTYWV", "GOVPARTYDE", "GOVPARTYVT", "GOVPARTYWI",
        "GOVPARTYRI", "GOVPARTYKS",
        # House races (individual competitive districts)
        "KXHOUSERACE", "HOUSEPA17", "HOUSEPA1", "HOUSEMI7",
        "HOUSENY18", "HOUSEAKAL", "HOUSEAZ1", "HOUSEAZ6",
        "HOUSEOH13", "HOUSEWI3", "HOUSEIA1", "HOUSEMN2",
        "HOUSENV1", "HOUSENV4", "HOUSETX28", "HOUSEMI8",
        "HOUSEPA8", "HOUSEAZ2", "HOUSEWI1",
        # Seat count / balance of power
        "RSENATESEATS", "KXDSENATESEATS", "KXRHOUSESEATS", "KXDSENATESEATSH",
        "KXCLOSESTSENATE", "KXGOVSENDIFF",
    ]
    # Note: HOUSECA40 removed — 0 open markets as of 2026-07-01 (settled/not yet open)

    # ------------------------------------------------------------------
    # Polymarket — which tag IDs and liquidity floor to use
    # ------------------------------------------------------------------
    POLYMARKET_GAMMA_BASE = "https://gamma-api.polymarket.com"
    POLYMARKET_CLOB_BASE  = "https://clob.polymarket.com"

    # Verified 2026-07-01:
    #   102289 = 2026 midterms (Senate/Governor seat-count + party control markets)
    #   105001 = Senate races (state-level R/D win markets)
    # Tags 100344 (House Races) and 933 (federal government) return no active markets.
    POLYMARKET_TAG_IDS: list[int] = [102289, 105001]

    # Minimum total liquidity (USD) for a market to be ingested
    POLYMARKET_MIN_LIQUIDITY: float = 25_000

    # ------------------------------------------------------------------
    # Cross-venue matching
    # ------------------------------------------------------------------
    SIMILARITY_THRESHOLD: float = 0.55
    JACCARD_WEIGHT: float = 0.6
    LEVENSHTEIN_WEIGHT: float = 0.4
