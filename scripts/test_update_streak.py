from datetime import date
import unittest
import xml.etree.ElementTree as ET
from update_streak import calculate, render


def stats(entries, today='2026-09-18'):
    return calculate({date.fromisoformat(day): count for day, count in entries.items()}, date.fromisoformat(today))


class StreakTests(unittest.TestCase):
    def test_latest_tie_wins_even_with_unsorted_input(self):
        result = stats({'2026-02-25': 6, '2024-05-09': 1, '2026-02-24': 1, '2024-05-10': 1})
        self.assertEqual(result['longest'], (2, date(2026, 2, 24), date(2026, 2, 25)))
        self.assertEqual(result['total'], 9)

    def test_longer_old_record_beats_shorter_recent_one(self):
        result = stats({'2024-05-09': 1, '2024-05-10': 1, '2024-05-11': 1, '2026-09-17': 5})
        self.assertEqual(result['longest'][0], 3)
        self.assertEqual(result['longest'][1], date(2024, 5, 9))
        self.assertEqual(result['current'][0], 1)

    def test_today_grace_then_expiration(self):
        entries = {'2026-09-16': 1, '2026-09-17': 5, '2026-09-18': 0}
        self.assertEqual(stats(entries)['current'][0], 2)
        self.assertEqual(stats(entries, '2026-09-19')['current'][0], 0)

    def test_new_record_spans_year_boundary(self):
        result = stats({'2025-12-30': 1, '2025-12-31': 1, '2026-01-01': 10}, '2026-01-01')
        self.assertEqual(result['current'][0], 3)
        self.assertEqual(result['longest'][0], 3)

    def test_empty_and_future_activity(self):
        result = stats({'2026-09-19': 5})
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['longest'][0], 0)
        ET.fromstring(render(result))

    def test_render_keeps_years_explicit(self):
        result = stats({'2026-02-24': 1, '2026-02-25': 6})
        svg = render(result)
        ET.fromstring(svg)
        self.assertIn('Feb 24, 2026 – Feb 25, 2026', svg)


if __name__ == '__main__':
    unittest.main()
