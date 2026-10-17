import unittest

from time_ordered_key_value_store import TimeOrderedKeyValueStore


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        self.t += 1.0
        return self.t


class TestInsert(unittest.TestCase):
    def test_insert_returns_timestamp_and_stores_value(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        ts = store.insert("a", 1)
        self.assertEqual(ts, 1.0)
        self.assertEqual(len(store), 1)
        self.assertEqual(store.all_records(), [(1.0, "a", 1)])

    def test_duplicate_keys_produce_multiple_records(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("k", "v1")
        store.insert("k", "v2")
        self.assertEqual(len(store), 2)
        self.assertEqual(store.all_records(),
                         [(1.0, "k", "v1"), (2.0, "k", "v2")])

    def test_explicit_timestamp_must_be_non_decreasing(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("a", 1, timestamp=10.0)
        with self.assertRaises(ValueError):
            store.insert("b", 2, timestamp=9.0)

    def test_explicit_timestamp_equal_is_allowed(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("a", 1, timestamp=5.0)
        store.insert("b", 2, timestamp=5.0)
        self.assertEqual(len(store), 2)

    def test_explicit_timestamp_clock_not_called(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("a", 1, timestamp=100.0)
        self.assertEqual(clock.t, 0.0)


class TestLatest(unittest.TestCase):
    def test_latest_returns_newest_last(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        for i in range(5):
            store.insert("k", i)
        latest = store.latest(3)
        self.assertEqual(latest, [(3.0, "k", 2), (4.0, "k", 3), (5.0, "k", 4)])

    def test_latest_more_than_available_returns_all(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("a", 1)
        self.assertEqual(store.latest(10), [(1.0, "a", 1)])

    def test_latest_zero_returns_empty(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("a", 1)
        self.assertEqual(store.latest(0), [])

    def test_latest_negative_raises(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        with self.assertRaises(ValueError):
            store.latest(-1)

    def test_latest_empty_store(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        self.assertEqual(store.latest(5), [])


class TestRange(unittest.TestCase):
    def test_range_inclusive_both_ends(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        for i in range(10):
            store.insert("k", i)  # ts 1..10
        result = store.range(3, 5)
        self.assertEqual([r[0] for r in result], [3.0, 4.0, 5.0])

    def test_range_open_start(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        for i in range(10):
            store.insert("k", i)
        result = store.range(None, 2)
        self.assertEqual([r[0] for r in result], [1.0, 2.0])

    def test_range_open_end(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        for i in range(10):
            store.insert("k", i)
        result = store.range(9, None)
        self.assertEqual([r[0] for r in result], [9.0, 10.0])

    def test_range_both_open_returns_all(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        for i in range(5):
            store.insert("k", i)
        self.assertEqual(len(store.range()), 5)

    def test_range_no_match(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        for i in range(5):
            store.insert("k", i)  # ts 1..5
        self.assertEqual(store.range(100, 200), [])

    def test_range_with_ties_at_boundary(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("a", 1, timestamp=5.0)
        store.insert("b", 2, timestamp=5.0)
        store.insert("c", 3, timestamp=5.0)
        result = store.range(5, 5)
        self.assertEqual(len(result), 3)
        self.assertEqual([r[1] for r in result], ["a", "b", "c"])

    def test_range_empty_store(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        self.assertEqual(store.range(1, 10), [])

    def test_range_before_first(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        for i in range(5):
            store.insert("k", i)  # ts 1..5
        self.assertEqual(store.range(-10, 0), [])


class TestIteration(unittest.TestCase):
    def test_iter_yields_insertion_order(self):
        clock = FakeClock()
        store = TimeOrderedKeyValueStore(clock=clock)
        store.insert("a", 1)
        store.insert("b", 2)
        self.assertEqual(list(store),
                         [(1.0, "a", 1), (2.0, "b", 2)])


class TestEmptyStore(unittest.TestCase):
    def test_len_zero(self):
        store = TimeOrderedKeyValueStore(clock=FakeClock())
        self.assertEqual(len(store), 0)

    def test_all_records_empty(self):
        store = TimeOrderedKeyValueStore(clock=FakeClock())
        self.assertEqual(store.all_records(), [])


if __name__ == "__main__":
    unittest.main()
