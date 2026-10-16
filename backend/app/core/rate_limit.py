"""Shared rate limiter (slowapi).

Kept in its own module so both the app factory and route modules can import it
without a circular dependency on ``app.main``.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address)


def solve_rate_limit() -> str:
    """Per-client limit string for expensive endpoints, e.g. ``"60/minute"``."""
    return f"{get_settings().rate_limit_per_minute}/minute"
