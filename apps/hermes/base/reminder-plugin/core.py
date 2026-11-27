"""Schedule and state transitions for Kepler reminders. No Discord or Hermes imports."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
KINDS = {"once", "daily", "weekly", "monthly", "dates"}


def utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("A timezone offset is required")
    return value.astimezone(timezone.utc)


def validate(spec, now=None):
    now = utc(now or datetime.now(timezone.utc))
    kind = spec.get("kind")
    if kind not in KINDS:
        raise ValueError("kind must be once, daily, weekly, monthly, or dates")
    ZoneInfo(spec.get("timezone", "America/Mexico_City"))
    if kind == "once":
        due = utc(spec["at"])
        if due <= now:
            raise ValueError("at must be in the future")
    elif kind == "dates":
        if not spec.get("dates") or not any(utc(item) > now for item in spec["dates"]):
            raise ValueError("dates must contain a future instant")
    else:
        times = spec.get("times")
        if not isinstance(times, list) or not times or len(times) > 12:
            raise ValueError("times must contain 1 to 12 HH:MM entries")
        for item in times:
            time.fromisoformat(item)
        if kind == "weekly" and not set(spec.get("weekdays", [])) <= WEEKDAYS.keys():
            raise ValueError("weekdays must use mon through sun")
        if kind == "weekly" and not spec.get("weekdays"):
            raise ValueError("weekly reminders need weekdays")
        if kind == "monthly" and (not spec.get("monthdays") or any(not 1 <= n <= 31 for n in spec["monthdays"])):
            raise ValueError("monthdays must contain numbers from 1 to 31")
    interval = spec.get("repeat_minutes")
    if interval is not None and (not isinstance(interval, int) or not 15 <= interval <= 10080):
        raise ValueError("repeat_minutes must be between 15 and 10080")
    if len(spec.get("title", "")) > 150 or not spec.get("title", "").strip():
        raise ValueError("title is required and must be at most 150 characters")
    if len(spec.get("details", "")) > 1500:
        raise ValueError("details must be at most 1500 characters")


def next_occurrence(spec, after):
    """Return the next UTC occurrence strictly after `after`. Invalid DST times skip."""
    after = utc(after)
    kind = spec["kind"]
    if kind == "once":
        candidate = utc(spec["at"])
        return candidate if candidate > after else None
    if kind == "dates":
        return min((utc(item) for item in spec["dates"] if utc(item) > after), default=None)
    zone = ZoneInfo(spec.get("timezone", "America/Mexico_City"))
    today = after.astimezone(zone).date()
    for offset in range(370):
        day = today + timedelta(days=offset)
        if kind == "weekly" and day.weekday() not in {WEEKDAYS[x] for x in spec["weekdays"]}:
            continue
        if kind == "monthly" and day.day not in spec["monthdays"]:
            continue
        for clock in sorted(spec["times"]):
            local = datetime.combine(day, time.fromisoformat(clock), tzinfo=zone)
            candidate = local.astimezone(timezone.utc)
            if candidate.astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
                continue
            if candidate > after:
                return candidate
    raise ValueError("No occurrence found within 370 days")


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY, spec TEXT NOT NULL, scheduled_at TEXT NOT NULL,
                next_at TEXT NOT NULL, pending_ack INTEGER NOT NULL DEFAULT 0,
                last_message_id TEXT, active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, spec, now=None):
        now = utc(now or datetime.now(timezone.utc))
        validate(spec, now)
        due = next_occurrence(spec, now)
        ident = uuid.uuid4().hex[:12]
        with self.connect() as db:
            db.execute("INSERT INTO reminders (id,spec,scheduled_at,next_at,created_at) VALUES (?,?,?,?,?)",
                       (ident, json.dumps(spec), due.isoformat(), due.isoformat(), now.isoformat()))
        return ident, due

    def list(self, active_only=True):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM reminders WHERE active=1 ORDER BY next_at" if active_only else
                              "SELECT * FROM reminders ORDER BY next_at").fetchall()
        return [dict(row) | {"spec": json.loads(row["spec"])} for row in rows]

    def cancel(self, ident):
        with self.connect() as db:
            return db.execute("UPDATE reminders SET active=0 WHERE id=? AND active=1", (ident,)).rowcount == 1

    def due(self, now=None):
        now = utc(now or datetime.now(timezone.utc))
        with self.connect() as db:
            rows = db.execute("SELECT * FROM reminders WHERE active=1 AND next_at<=? ORDER BY next_at", (now.isoformat(),)).fetchall()
        return [dict(row) | {"spec": json.loads(row["spec"])} for row in rows]

    def next_due(self):
        with self.connect() as db:
            row = db.execute("SELECT MIN(next_at) FROM reminders WHERE active=1").fetchone()
        return utc(row[0]) if row[0] else None

    def delivered(self, ident, due_at, message_id, now=None):
        now = utc(now or datetime.now(timezone.utc))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM reminders WHERE id=? AND active=1 AND next_at=?", (ident, due_at)).fetchone()
            if not row:
                return False
            spec = json.loads(row["spec"])
            scheduled = utc(row["scheduled_at"])
            if spec.get("repeat_minutes"):
                next_at = now + timedelta(minutes=spec["repeat_minutes"])
                active = 1
            else:
                next_at = next_occurrence(spec, scheduled)
                active = 1  # Keep a one-shot card actionable until acknowledged.
                if next_at is None:
                    next_at = datetime.max.replace(tzinfo=timezone.utc)
            db.execute("UPDATE reminders SET next_at=?,scheduled_at=?,pending_ack=?,last_message_id=?,active=? WHERE id=?",
                       ((next_at or now).isoformat(), (next_at or scheduled).isoformat() if not spec.get("repeat_minutes") else scheduled.isoformat(),
                        int(bool(spec.get("repeat_minutes"))), str(message_id), active, ident))
        return True

    def act(self, ident, message_id, action, now=None):
        now = utc(now or datetime.now(timezone.utc))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM reminders WHERE id=? AND active=1 AND last_message_id=?", (ident, str(message_id))).fetchone()
            if not row:
                return "stale"
            spec = json.loads(row["spec"])
            if action == "done":
                next_at = next_occurrence(spec, max(utc(row["scheduled_at"]), now)) if spec.get("repeat_minutes") else utc(row["next_at"])
                active = int(next_at is not None and next_at.year < 9999)
                db.execute("UPDATE reminders SET next_at=?,scheduled_at=?,pending_ack=0,last_message_id=NULL,active=? WHERE id=?",
                           ((next_at or now).isoformat(), (next_at or now).isoformat(), active, ident))
            elif action in {"snooze_1h", "snooze_1d"}:
                next_at = now + (timedelta(hours=1) if action == "snooze_1h" else timedelta(days=1))
                db.execute("UPDATE reminders SET next_at=?,pending_ack=1,last_message_id=NULL WHERE id=?", (next_at.isoformat(), ident))
            else:
                raise ValueError("Unknown action")
        return "ok"
