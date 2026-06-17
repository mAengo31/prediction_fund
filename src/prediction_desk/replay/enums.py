"""Replay harness enumerations."""

from __future__ import annotations

from enum import StrEnum


class ReplayRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
