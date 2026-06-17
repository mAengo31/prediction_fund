"""Decimal-only liquidity helpers."""

from __future__ import annotations

from decimal import Decimal

from prediction_desk.domain.models import PriceLevel


def best_bid(levels: list[PriceLevel]) -> Decimal | None:
    return max((level.price for level in levels), default=None)


def best_ask(levels: list[PriceLevel]) -> Decimal | None:
    return min((level.price for level in levels), default=None)


def total_depth(levels: list[PriceLevel]) -> Decimal:
    return sum((level.quantity for level in levels), Decimal("0"))


def depth_at_price(levels: list[PriceLevel], price: Decimal | None) -> Decimal:
    if price is None:
        return Decimal("0")
    return sum((level.quantity for level in levels if level.price == price), Decimal("0"))


def mid_price(bid: Decimal | None, ask: Decimal | None) -> Decimal | None:
    if bid is None or ask is None:
        return None
    return (bid + ask) / Decimal("2")


def spread(bid: Decimal | None, ask: Decimal | None) -> Decimal | None:
    if bid is None or ask is None:
        return None
    return ask - bid


def spread_bps(spread_value: Decimal | None, mid_value: Decimal | None) -> Decimal | None:
    if spread_value is None or mid_value is None or mid_value == 0:
        return None
    return (spread_value / mid_value) * Decimal("10000")


def book_imbalance(bid_depth: Decimal, ask_depth: Decimal) -> Decimal | None:
    denominator = bid_depth + ask_depth
    if denominator == 0:
        return None
    return (bid_depth - ask_depth) / denominator
