"""Focused state and scheduling checks; run with python -m unittest."""

import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("reminder_core", Path(__file__).with_name("core.py"))
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class ReminderTests(unittest.TestCase):
    def test_daily_timezone_and_multiple_times(self):
        schedule = {"title": "Backup", "kind": "daily", "timezone": "America/Mexico_City", "times": ["08:00", "18:00"]}
        self.assertEqual(core.next_occurrence(schedule, "2026-11-27T15:00:00Z"),
                         datetime.fromisoformat("2026-11-28T00:00:00+00:00"))

    def test_monthly_skips_short_month(self):
        schedule = {"title": "Review", "kind": "monthly", "monthdays": [31], "times": ["09:00"]}
        self.assertEqual(core.next_occurrence(schedule, "2026-04-01T00:00:00Z").month, 5)

    def test_repeat_ack_snooze_and_restart(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.db"
            store = core.Store(path)
            now = datetime.fromisoformat("2026-11-27T12:00:00+00:00")
            ident, due = store.create({"title": "Rotate PAT", "kind": "once", "at": "2026-11-27T13:00:00Z",
                                       "repeat_minutes": 1440}, now)
            self.assertEqual(len(store.due("2026-11-27T13:00:00Z")), 1)
            self.assertTrue(store.delivered(ident, due.isoformat(), "123", "2026-11-27T13:00:00Z"))
            restarted = core.Store(path)
            self.assertEqual(restarted.act(ident, "wrong", "done"), "stale")
            self.assertEqual(restarted.act(ident, "123", "snooze_1h", "2026-11-27T13:05:00Z"), "ok")
            self.assertEqual(len(restarted.due("2026-11-27T14:04:00Z")), 0)
            self.assertEqual(len(restarted.due("2026-11-27T14:05:00Z")), 1)
            self.assertTrue(restarted.delivered(ident, "2026-11-27T14:05:00+00:00", "124", "2026-11-27T14:05:00Z"))
            self.assertEqual(restarted.act(ident, "124", "done", "2026-11-27T14:06:00Z"), "ok")
            self.assertEqual(restarted.list(), [])

    def test_one_shot_stays_actionable(self):
        with tempfile.TemporaryDirectory() as root:
            store = core.Store(Path(root) / "state.db")
            ident, due = store.create({"title": "Test", "kind": "once", "at": "2026-11-27T13:00:00Z"},
                                      "2026-11-27T12:00:00Z")
            store.delivered(ident, due.isoformat(), "50", due)
            self.assertEqual(store.act(ident, "50", "done", due), "ok")
            self.assertEqual(store.list(), [])


if __name__ == "__main__":
    unittest.main()
