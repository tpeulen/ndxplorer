"""DataSource queries run in tttrlib's DataStore."""

import unittest

import numpy as np

from ndxplorer.core.data_source import DataSource

#: Each query, with the same predicate written out in numpy.
QUERIES = [
    ("(g>2) & (r<10)", lambda g, r, b: (g > 2) & (r < 10)),
    ("g>5 | b<0.1", lambda g, r, b: (g > 5) | (b < 0.1)),
    ("~(g>2) & (r>1)", lambda g, r, b: ~(g > 2) & (r > 1)),
    ("(g-b)/(r-b) > 0.3", lambda g, r, b: (g - b) / (r - b) > 0.3),
    ("g>2 and r<10", lambda g, r, b: (g > 2) & (r < 10)),
    ("g != 3", lambda g, r, b: g != 3),
]


def frame(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    return {"g": rng.uniform(0, 10, n),
            "r": rng.uniform(0, 20, n),
            "b": rng.uniform(0, 1, n)}


class BffQueryTests(unittest.TestCase):
    def setUp(self):
        self.frame = frame()
        self.source = DataSource.from_columns(self.frame)

    def test_every_query_matches_numpy(self):
        f = self.frame
        for query, predicate in QUERIES:
            np.testing.assert_array_equal(
                self.source.query_mask(query),
                predicate(f["g"], f["r"], f["b"]), err_msg=query)

    def test_count_matches_the_mask(self):
        for query, _ in QUERIES:
            self.assertEqual(self.source.query_count(query),
                             int(self.source.query_mask(query).sum()), query)

    def test_an_unknown_parameter_is_refused(self):
        with self.assertRaises(ValueError):
            self.source.query_mask("nosuch > 1")

    def test_queries_reuse_the_one_store(self):
        self.source.query_mask("g > 1")
        first = self.source.store
        self.source.query_mask("r < 5")
        self.assertIs(self.source.store, first)

    def test_a_query_answers_without_changing_the_store_selection(self):
        """A query is a question, not a gate: the store's own selection is left
        as it was, so the gates evaluated in it are undisturbed."""
        store = self.source.store
        self.assertFalse(store.has_row_mask())
        self.source.query_mask("g > 5")
        self.assertFalse(store.has_row_mask())
        keep = np.zeros(len(self.frame["g"]), dtype=bool)
        keep[::3] = True
        store.select(keep)
        self.source.query_mask("r < 5")
        np.testing.assert_array_equal(store.selection(), keep)

if __name__ == "__main__":
    unittest.main()
