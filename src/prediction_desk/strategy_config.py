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
        # Senate races (state-level)
        "SENATEOK", "SENATEAL", "SENATERI", "SENATEAK", "SENATEMS",
        "SENATEPA", "SENATECT", "SENATEMD", "SENATEMA", "SENATEWA",
        "SENATEOHS", "SENATEUT", "SENATEMT", "SENATEAR", "SENATEIL",
        "SENATEND",
        # Governor races
        "GOVPARTYFL", "GOVPARTYGA", "GOVPARTYSC", "GOVPARTYOR",
        "GOVPARTYIA", "GOVPARTYME", "GOVPARTYMA", "GOVPARTYMT",
        "GOVPARTYMD", "GOVPARTYMI",
        # House races (individual districts)
        "KXHOUSERACE", "HOUSEPA17", "HOUSEPA1", "HOUSEMI7",
        "HOUSENY18", "HOUSEAKAL", "HOUSEAZ1", "HOUSEAZ6",
        "HOUSECA40", "HOUSEOH13", "HOUSEWI3", "HOUSEIA1",
        "HOUSEMN2", "HOUSENV1", "HOUSENV4",
        # Seat count markets
        "RSENATESEATS", "KXDSENATESEATS", "KXRHOUSESEATS", "KXDSENATESEATSH",
        # Closest/balance of power
        "KXCLOSESTSENATE", "KXGOVSENDIFF",
    ]

    # ------------------------------------------------------------------
    # Polymarket — which tag IDs and liquidity floor to use
    # ------------------------------------------------------------------
    POLYMARKET_GAMMA_BASE = "https://gamma-api.polymarket.com"
    POLYMARKET_CLOB_BASE  = "https://clob.polymarket.com"

    # 102289 = midterms, 105001 = senate-races
    POLYMARKET_TAG_IDS: list[int] = [102289, 105001]

    # Minimum total liquidity (USD) for a market to be ingested
    POLYMARKET_MIN_LIQUIDITY: float = 25_000

    # ------------------------------------------------------------------
    # Cross-venue matching
    # ------------------------------------------------------------------
    # Minimum similarity score (0–1) for two markets to be considered a match
    SIMILARITY_THRESHOLD: float = 0.55

    # Jaccard token overlap weight vs Levenshtein string similarity weight
    JACCARD_WEIGHT: float = 0.6
    LEVENSHTEIN_WEIGHT: float = 0.4
