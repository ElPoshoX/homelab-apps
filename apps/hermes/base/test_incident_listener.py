"""Focused tests for incident decision delivery and recovery verification."""

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("incident-listener.py")


def load_listener():
    spec = importlib.util.spec_from_file_location("incident_listener_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {
        "DISCORD_BOT_TOKEN": "test-token",
        "INCIDENT_API_SERVER_KEY": "test-key",
        "KEPLER_INCIDENT_OWNER_ID": "12345",
    }), patch.dict(sys.modules, {"discord": types.ModuleType("discord")}):
        spec.loader.exec_module(module)
    return module


class IncidentListenerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.listener = load_listener()
        self.listener.DB_PATH = Path(self.temp.name) / "incidents.sqlite3"
        self.listener.initialize()

    def test_existing_cases_gain_decision_column_without_data_loss(self):
        with self.listener.connect() as db:
            db.execute("INSERT INTO incident_cases(case_key,alert_name,scope,state,source_id,source_url) "
                       "VALUES ('case','DNS','cluster','firing','100','https://example.test')")
            db.execute("ALTER TABLE incident_cases DROP COLUMN decision_notified")
        self.listener.initialize()
        self.assertEqual(self.listener.case("case")["decision_notified"], 0)

    def test_decision_pings_owner_once_and_resolved_alert_is_verified(self):
        listener = self.listener
        calls = []
        decision = {"summary": "DNS is unavailable in one zone.", "recommended": 1,
                    "options": [
                        {"label": "Restart one replica", "effect": "Restore DNS", "risk": "Brief loss", "rollback": "Revert rollout"},
                        {"label": "Defer", "effect": "Leave outage", "risk": "Longer impact", "rollback": "None"}]}
        reports = iter(["DECISION_REQUIRED:" + json.dumps(decision),
                        "Restarted one replica; DNS and metrics verified.",
                        "Service healthy; metrics and DNS check pass."])

        def discord_api(path, *, method="GET", body=None):
            calls.append((method, path, body))
            if method == "GET":
                return {"thread": {"id": "thread"}}
            if method == "POST" and path.endswith("/messages") and body.get("embeds"):
                return {"id": "status"}
            return {"id": "notice"}

        def hermes_api(*args, **kwargs):
            return {"choices": [{"message": {"content": next(reports)}}]}

        with patch.object(listener, "discord_api", side_effect=discord_api), \
             patch.object(listener, "request_json", side_effect=hermes_api):
            firing = ("100", "firing", "🚨 Firing · DNS", "**Scope:** cluster", "https://example.test")
            listener.process_event(firing)
            listener.process_event(firing)
            notices = [body for method, _, body in calls if method == "POST" and body.get("content")]
            self.assertEqual(len(notices), 1)
            self.assertEqual(notices[0]["allowed_mentions"], {"users": ["12345"]})
            self.assertTrue(notices[0]["enforce_nonce"])
            self.assertEqual(listener.case('["dns", "cluster"]')["decision_notified"], 1)
            card = next(body for method, path, body in calls
                        if method == "PATCH" and path.endswith("/messages/status"))
            self.assertEqual(len(card["components"][0]["components"]), 3)
            self.assertIn("Otra propuesta", card["components"][0]["components"][-1]["label"])

            selected = listener.claim_choice("100", {"kind": "option", "number": 1, **decision["options"][0]})
            self.assertIsNotNone(selected)
            self.assertIsNone(listener.claim_choice("100", {"kind": "option", "number": 2}))
            listener.complete_choice(selected)
            self.assertEqual(listener.case('["dns", "cluster"]')["decision_state"], "complete")

            resolved = ("101", "resolved", "✅ Resolved · DNS", "**Scope:** cluster", "https://example.test")
            listener.process_event(resolved)
            self.assertEqual(listener.case('["dns", "cluster"]')["resolved_posted"], 1)
            self.assertEqual(len([body for method, _, body in calls
                                  if method == "POST" and body.get("content")]), 2)

    def test_malformed_decision_keeps_original_without_rerunning_agent(self):
        listener = self.listener
        with listener.connect() as db:
            db.execute("INSERT INTO incident_cases(case_key,alert_name,scope,state,source_id,source_url) "
                       "VALUES ('case','DNS','cluster','firing','100','https://example.test')")
        listener.save_report("case", "DECISION_REQUIRED: I need a decision but forgot JSON")
        item = listener.case("case")
        self.assertEqual(item["decision_state"], "pending")
        decision = listener.decision_from_report(item["report"])
        self.assertEqual(len(decision["options"]), 2)
        self.assertIn("forgot JSON", decision["summary"])


if __name__ == "__main__":
    unittest.main()
