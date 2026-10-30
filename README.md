# time_ordered_key_value_store

An in-memory key-value store that indexes entries by insertion timestamp, supporting efficient range queries over time and retrieval of the most recent N entries. Standard library only.

## Usage

```python
from time_ordered_key_value_store import TimeOrderedKeyValueStore

store = TimeOrderedKeyValueStore()
store.insert("sensor_1", 42.0)
store.insert("sensor_1", 43.0)

recent = store.latest(2)        # newest N records, newest-last
window = store.range(0, 10)     # records with 0 <= ts <= 10
```

## Why

For audit logs and time-series snapshots, the question "what happened between T1 and T2?" is asked far more often than "give me the latest value for key K." This library optimizes for that case: an append-ordered record list plus a parallel time index lets both range and latest queries run in O(log n + k) via `bisect`, with no dependencies.

The trade-off: keys are not unique. Inserting the same key twice creates two records. This keeps the time axis authoritative — essential for audit-style data — at the cost of a separate scan if the caller needs "latest value for a specific key."

## Edge cases

- Timestamps must be non-decreasing. Passing an explicit `timestamp` older than the most recent record raises `ValueError` rather than silently reordering history.
- Tied timestamps at a range boundary are included: `range(5, 5)` returns all records at `5`, on both sides.
- `latest(n)` returns records newest-last (insertion order). Call `reversed()` if you need newest-first.
- For deterministic tests, pass a fake `clock` function to the constructor. The default clock uses `time.time()`.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

