"""Every recorded original exchange must replay through the era-appropriate policy."""
import unittest
from tools import coverage


class CoverageAuditTests(unittest.TestCase):
    def test_all_recorded_exchanges_replay_without_mismatch(self):
        rows = coverage.load()
        self.assertGreater(len(rows), 1000)
        mismatches, cells = coverage.replay(rows)
        self.assertEqual(mismatches, [])
        self.assertGreater(sum(cells.values()), 400)

    def test_era_boundaries(self):
        self.assertEqual(coverage.era("2026-10-10T16:20:34+00:00"), "v1")
        self.assertEqual(coverage.era("2026-10-10T20:55:00+00:00"), "uncertain")
        self.assertEqual(coverage.era("2026-10-10T21:00:15+00:00"), "v2")

    def test_gap_report_names_only_unobserved_cells(self):
        import collections
        cells = collections.Counter({("v2", "PING", "200"): 1})
        missing = coverage.gaps(cells, "v2")
        self.assertNotIn(("PING", "200"), missing)
        self.assertIn(("PING", "E103"), missing)


if __name__ == "__main__":
    unittest.main()
