"""Quote sanitation and the four-second rolling median.

A tick is rejected before it can enter the window. The last good package
median stays in force until a new valid one exists. If that value is older
than STALE_SEC, it is not tradable.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from statistics import median


WINDOW_SEC = 4.0
STALE_SEC = 8.0
MIN_SAMPLES = 5
MAX_LEG_WIDTH = 0.20
MAX_JUMP = 0.15
MAX_MODEL_GAP = 0.20


@dataclass
class LegQuote:
    bid: float
    ask: float
    ts: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    def reject_reason(self) -> str | None:
        if self.bid <= 0 or self.ask <= 0:
            return "leg has no two-sided market"
        if self.bid > self.ask:
            return "leg market is crossed"
        if self.ask - self.bid > MAX_LEG_WIDTH:
            return "leg spread is wider than 20 cents"
        return None


@dataclass
class PackageQuote:
    """Net price of the order being worked. Positive means a credit to us
    when selling, or a debit we would pay when buying to close. `side` is
    'credit' or 'debit' and is the sign the order is supposed to have."""

    price: float
    side: str
    ts: float
    underlying: float
    model: float | None = None


@dataclass
class MedianState:
    value: float | None = None
    samples: int = 0
    last_good_ts: float | None = None
    last_reject: str | None = None
    tradable: bool = False


class QuoteBook:
    def __init__(self) -> None:
        self._window: deque[tuple[float, float]] = deque()
        self.state = MedianState()
        self._last_underlying: float | None = None

    def consider(self, legs: list[LegQuote], package: PackageQuote) -> MedianState:
        if len(legs) < 2:
            return self._reject("package is missing legs")
        times = [leg.ts for leg in legs]
        if max(times) - min(times) > 1.0:
            return self._reject("leg quotes are more than a second apart")
        for leg in legs:
            reason = leg.reject_reason()
            if reason:
                return self._reject(reason)
        if package.side == "credit" and package.price <= 0:
            return self._reject("opening package flipped from credit to debit")
        if package.side == "debit" and package.price <= 0:
            return self._reject("closing package has no positive price")
        if self.state.value is not None and abs(package.price - self.state.value) > MAX_JUMP:
            moved = 0.0 if self._last_underlying is None else abs(package.underlying - self._last_underlying)
            if moved < 0.15:
                return self._reject("package jumped without the underlying moving")
        if package.model is not None and abs(package.price - package.model) > MAX_MODEL_GAP:
            return self._reject("package is more than 20 cents from the model")
        self._window.append((package.ts, package.price))
        self._last_underlying = package.underlying
        self._trim(package.ts)
        prices = [price for _, price in self._window]
        self.state.samples = len(prices)
        self.state.last_reject = None
        if len(prices) >= MIN_SAMPLES:
            # A limit is a whole cent. 0.8397 is not a price anyone can send.
            self.state.value = round(float(median(prices)), 2)
            self.state.last_good_ts = package.ts
        self.state.tradable = self._is_fresh(package.ts)
        return self.state

    def mark_time(self, now: float) -> MedianState:
        self._trim(now)
        self.state.samples = len(self._window)
        self.state.tradable = self._is_fresh(now)
        return self.state

    def _trim(self, now: float) -> None:
        while self._window and now - self._window[0][0] > WINDOW_SEC:
            self._window.popleft()

    def _is_fresh(self, now: float) -> bool:
        if self.state.value is None or self.state.last_good_ts is None:
            return False
        return now - self.state.last_good_ts <= STALE_SEC and self.state.samples >= MIN_SAMPLES

    def _reject(self, reason: str) -> MedianState:
        self.state.last_reject = reason
        self.state.tradable = self._is_fresh(self._window[-1][0] if self._window else 0.0)
        return self.state
