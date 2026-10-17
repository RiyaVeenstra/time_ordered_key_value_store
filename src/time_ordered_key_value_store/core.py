from __future__ import annotations

import bisect
from typing import Callable, Iterator, List, Optional, Tuple

__all__ = ["TimeOrderedKeyValueStore"]


class TimeOrderedKeyValueStore:
    """An in-memory key-value store indexed by monotonic insertion time.

    The store keeps an append-ordered list of (timestamp, key, value) records
    plus a ``SortedList``-style time index so that range queries by timestamp
    and "most recent N" queries are both binary-search fast. Key uniqueness is
    NOT required: inserting the same key twice creates two records. This keeps
    the time axis authoritative — useful for audit logs — at the cost of a
    separate lookup if the caller needs "latest value for key". That
    trade-off is deliberate: ordering by wall clock is the core feature here.

    Timestamps must be comparable via ``<`` / ``<=``. For deterministic
    behaviour, pass an injective ``clock`` function in tests.
    """

    def __init__(
        self,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        # ``_times`` mirrors ``_records`` 1:1 and stays non-decreasing because we
        # derive timestamps from a single monotonic clock in the common case.
        # Even with an injective fake clock (strictly increasing) or an equal
        # clock (ties), non-decreasing is preserved, which is the only
        # invariant ``bisect`` requires.
        self._clock = clock if clock is not None else self._default_clock
        self._records: List[Tuple[float, str, object]] = []
        self._times: List[float] = []

    @staticmethod
    def _default_clock() -> float:
        import time

        return time.time()

    def insert(
        self,
        key: str,
        value: object,
        *,
        timestamp: Optional[float] = None,
    ) -> float:
        """Store ``value`` under ``key`` and return the record's timestamp.

        A custom ``timestamp`` lets callers replay historical events in
        order. It must be ``>=`` the last record's timestamp to keep the
        underlying time index non-decreasing; otherwise a ``ValueError`` is
        raised — silently reordering history would be a worse failure mode
        than a loud crash.
        """
        ts = self._clock() if timestamp is None else timestamp
        if self._times and ts < self._times[-1]:
            raise ValueError(
                "timestamp is older than the most recent record; "
                "time must stay non-decreasing"
            )
        self._records.append((ts, key, value))
        self._times.append(ts)
        return ts

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[Tuple[float, str, object]]:
        return iter(self._records)

    def latest(self, n: int = 1) -> List[Tuple[float, str, object]]:
        """Return the last ``n`` records, newest-last. ``n < 0`` raises.

        We slice rather than re-sort so the returned list is in insertion
        order; the caller can ``reversed()`` if they want newest-first.
        """
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return []
        return list(self._records[-n:])

    def range(
        self,
        start: Optional[float] = None,
        end: Optional[float] = None,
    ) -> List[Tuple[float, str, object]]:
        """Return records with ``start <= ts <= end``, in time order.

        ``None`` means unbounded on that side. We use ``bisect_left`` for
        the start and ``bisect_right`` for the end so that, when timestamps
        tie at a boundary, all tied records are included on the inclusive
        side — the least surprising choice for audit-style data.
        """
        lo = bisect.bisect_left(self._times, start) if start is not None else 0
        hi = (
            bisect.bisect_right(self._times, end)
            if end is not None
            else len(self._times)
        )
        if lo > hi:
            return []
        return list(self._records[lo:hi])

    def all_records(self) -> List[Tuple[float, str, object]]:
        """Return a copy of every record in insertion order."""
        return list(self._records)
