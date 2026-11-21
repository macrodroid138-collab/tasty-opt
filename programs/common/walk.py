"""Six-step order walk.

Attempts 1–3 work the median and only reprice when the new median is worse.
Attempt 4 is the then-current median, two cents worse.
Attempt 6 is the then-current median, five cents worse. The five cents
replaces the two. It is not added on top.

If the current median has fallen more than five cents from the first fire,
the walk aborts. Urgent orders (a touch, a far-wing buyback, the $100 stop)
use two steps only, and skip straight to the five-cent concession when the
underlying has already run another point through the trigger.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WalkStatus:
    attempt: int = 0
    first_median: float | None = None
    working: float | None = None
    phase: str = "idle"  # idle, working, filled, aborted
    note: str = ""
    history: list[str] = field(default_factory=list)


class OrderWalk:
    def __init__(self, urgent: bool = False) -> None:
        self.urgent = urgent
        self.max_attempts = 2 if urgent else 6
        self.status = WalkStatus()

    def start(self, median: float, blown_through: bool = False) -> WalkStatus:
        self.status = WalkStatus(attempt=1, first_median=median, working=median, phase="working")
        if self.urgent and blown_through:
            self.status.working = self._worse(median, 0.05)
            self.status.note = "underlying already through the trigger; working five cents worse than the median"
        else:
            self.status.note = "working the median"
        self.status.history.append(f"attempt 1 at {self.status.working:.2f}")
        return self.status

    def unfilled(self, current_median: float | None) -> WalkStatus:
        st = self.status
        if st.phase != "working":
            return st
        if current_median is None:
            st.note = "no tradable median; order left working"
            return st
        assert st.first_median is not None and st.working is not None
        if self._is_worse(current_median, st.first_median - 0.05):
            st.phase = "aborted"
            st.note = "median fell more than five cents from the first fire; order cancelled"
            st.history.append(st.note)
            return st
        st.attempt += 1
        if st.attempt > self.max_attempts:
            st.phase = "aborted"
            st.note = "walk finished without a fill"
            st.history.append(st.note)
            return st
        if self.urgent:
            price = self._worse(current_median, 0.05)
            note = "urgent second step, five cents worse than the current median"
        elif st.attempt <= 3 or st.attempt == 5:
            if self._is_worse(current_median, st.working):
                price = current_median
                note = "median worsened; replaced at the new median"
            else:
                price = st.working
                note = "median held or improved; resubmitted at the previous price"
        elif st.attempt == 4:
            price = self._worse(current_median, 0.02)
            note = "three tries unfilled; two cents worse than the current median"
        else:
            price = self._worse(current_median, 0.05)
            note = "last try; five cents worse than the current median"
        st.working = price
        st.note = note
        st.history.append(f"attempt {st.attempt} at {price:.2f}: {note}")
        return st

    def fill(self) -> WalkStatus:
        self.status.phase = "filled"
        self.status.note = f"filled at {self.status.working:.2f}" if self.status.working is not None else "filled"
        self.status.history.append(self.status.note)
        return self.status

    @staticmethod
    def _worse(median: float, concession: float) -> float:
        """A lower number is always a worse price for us: less credit when
        selling, and we store buy-to-close limits as a positive debit that
        gets larger when worse. Callers pass the debit as a positive number
        too, so worse means a larger debit. The sign lives on the order,
        not here: this helper subtracts for credits and the runtime adds
        for debits by passing a negated median. See runtime.worse_price."""
        return median - concession

    @staticmethod
    def _is_worse(price: float, than: float) -> bool:
        return price < than - 1e-9
