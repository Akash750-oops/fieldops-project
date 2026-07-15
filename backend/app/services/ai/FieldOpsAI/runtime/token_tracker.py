"""
token_tracker.py

Tracks Groq free-tier usage.

Responsibilities
----------------
- Track daily token usage.
- Track daily request count.
- Enforce configurable daily limits.
- Automatically reset counters every day.

This implementation uses in-memory storage.
It can later be replaced with Redis or PostgreSQL
without changing the public interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from threading import Lock


@dataclass
class UsageStatus:
    """
    Current usage statistics.
    """

    used_tokens: int
    remaining_tokens: int
    used_requests: int
    remaining_requests: int
    budget_available: bool


class TokenTracker:
    """
    Tracks Groq API usage.
    """

    DAILY_TOKEN_LIMIT = 1_400_000
    DAILY_REQUEST_LIMIT = 1_500

    def __init__(self) -> None:

        self._lock = Lock()

        self._current_day = date.today()

        self._used_tokens = 0

        self._used_requests = 0

    # ---------------------------------------------------------

    def _reset_if_needed(self) -> None:
        """
        Reset counters when a new day starts.
        """

        today = date.today()

        if today != self._current_day:

            self._current_day = today

            self._used_tokens = 0

            self._used_requests = 0

    # ---------------------------------------------------------

    def record_usage(
        self,
        tokens: int,
    ) -> None:
        """
        Record token usage for one request.
        """

        with self._lock:

            self._reset_if_needed()

            self._used_tokens += max(tokens, 0)

            self._used_requests += 1

    # ---------------------------------------------------------

    def can_make_request(
        self,
        estimated_tokens: int,
    ) -> bool:
        """
        Check whether another request
        can be sent safely.
        """

        with self._lock:

            self._reset_if_needed()

            if self._used_requests >= self.DAILY_REQUEST_LIMIT:
                return False

            if (
                self._used_tokens + estimated_tokens
                > self.DAILY_TOKEN_LIMIT
            ):
                return False

            return True

    # ---------------------------------------------------------

    def get_status(self) -> UsageStatus:
        """
        Return current usage statistics.
        """

        with self._lock:

            self._reset_if_needed()

            remaining_tokens = max(
                self.DAILY_TOKEN_LIMIT - self._used_tokens,
                0,
            )

            remaining_requests = max(
                self.DAILY_REQUEST_LIMIT - self._used_requests,
                0,
            )

            return UsageStatus(
                used_tokens=self._used_tokens,
                remaining_tokens=remaining_tokens,
                used_requests=self._used_requests,
                remaining_requests=remaining_requests,
                budget_available=(
                    remaining_tokens > 0
                    and remaining_requests > 0
                ),
            )

    # ---------------------------------------------------------

    def reset(self) -> None:
        """
        Reset counters manually.

        Intended mainly for unit tests.
        """

        with self._lock:

            self._current_day = date.today()

            self._used_tokens = 0

            self._used_requests = 0



token_tracker = TokenTracker()