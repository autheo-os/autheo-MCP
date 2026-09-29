"""
Autheo MCP service utilities.
"""

from __future__ import annotations

from typing import Any


def safe_int(value: Any, default: int | None = None) -> int | None:
    """
    Coerce a value to int, returning default on failure.
    """

    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float | None = None) -> float | None:
    """
    Coerce a value to float, returning default on failure.
    """

    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def mib_to_gb(mib: int | None) -> float | None:
    if mib is None:
        return None
    return round(mib / 1024, 2)


def gib_to_gb(gib: int | None) -> float | None:
    if gib is None:
        return None
    return round(gib, 2)
