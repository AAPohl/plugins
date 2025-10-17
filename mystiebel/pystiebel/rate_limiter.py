"""Rate limiter for API calls."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, TypeVar

from .const import API_RATE_LIMIT_DELAY

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, min_interval: float = API_RATE_LIMIT_DELAY) -> None:
        """Initialize the rate limiter.

        Args:
            min_interval: Minimum seconds between API calls
        """
        self._min_interval = timedelta(seconds=min_interval)
        self._last_call: datetime | None = None
        self._lock = asyncio.Lock()

    async def __call__(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute the function with rate limiting.

        Args:
            func: The async function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call
        """
        async with self._lock:
            now = datetime.now()

            # Calculate time to wait
            if self._last_call:
                elapsed = now - self._last_call
                if elapsed < self._min_interval:
                    wait_time = (self._min_interval - elapsed).total_seconds()
                    _LOGGER.debug("Rate limiting: waiting %.2f seconds", wait_time)
                    await asyncio.sleep(wait_time)

            # Update last call time and execute
            self._last_call = datetime.now()
            return await func(*args, **kwargs)

    def reset(self) -> None:
        """Reset the rate limiter."""
        self._last_call = None