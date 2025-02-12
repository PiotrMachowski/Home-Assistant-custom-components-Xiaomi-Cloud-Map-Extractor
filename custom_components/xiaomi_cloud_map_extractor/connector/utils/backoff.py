import asyncio
import random
from typing import Self


class Backoff:
    """Exponential backoff with jitter."""

    def __init__(self: Self, min_sleep: float, max_sleep: float) -> None:
        self._min_sleep = min_sleep
        self._sleep = min_sleep
        self._max_sleep = max_sleep

    async def sleep(self: Self) -> None:
        await asyncio.sleep(self._get_sleep_time())

    def reset(self: Self) -> None:
        self._sleep = self._min_sleep

    def _get_sleep_time(self: Self) -> float:
        self._sleep = min(self._max_sleep, random.uniform(self._min_sleep, self._sleep * 3))
        return self._sleep
