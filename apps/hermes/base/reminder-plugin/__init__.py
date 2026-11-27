"""Kepler reminder plugin for Hermes. Discord delivery never invokes an LLM."""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from plugins.plugin_storage import plugin_data_dir

from .core import Store

log = logging.getLogger(__name__)
_store = None
_wake = None
_loop = None


def _result(value):
    return json.dumps(value, ensure_ascii=False)


def _create(args, **kwargs):
    try:
        spec = {key: value for key, value in args.items() if value is not None}
        ident, due = _store.create(spec)
        if _wake and _loop:
            _loop.call_soon_threadsafe(_wake.set)
        return _result({"id": ident, "next_at": due.isoformat(), "status": "scheduled"})
    except (ValueError, KeyError, TypeError) as exc:
        return _result({"error": str(exc)})


def _list(args, **kwargs):
    return _result({"reminders": [{"id": row["id"], "title": row["spec"]["title"],
                                   "next_at": row["next_at"], "pending_ack": bool(row["pending_ack"])}
                                  for row in _store.list()]})


def _cancel(args, **kwargs):
    return _result({"cancelled": _store.cancel(args.get("id", ""))})


CREATE = {"name": "reminder_create", "description": "Schedule a durable Kepler reminder in Discord. Use repeat_minutes only when it must repeat until the owner acknowledges a card.",
          "parameters": {"type": "object", "properties": {
              "title": {"type": "string"}, "details": {"type": "string"},
              "kind": {"type": "string", "enum": ["once", "daily", "weekly", "monthly", "dates"]},
              "at": {"type": "string", "description": "ISO 8601 instant with timezone offset for once"},
              "dates": {"type": "array", "items": {"type": "string"}, "description": "ISO 8601 instants with offsets"},
              "times": {"type": "array", "items": {"type": "string"}, "description": "Local HH:MM times, up to 12 per day"},
              "weekdays": {"type": "array", "items": {"type": "string", "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}},
              "monthdays": {"type": "array", "items": {"type": "integer"}},
              "timezone": {"type": "string", "description": "IANA timezone; default America/Mexico_City"},
              "repeat_minutes": {"type": "integer", "description": "Optional 15–10080 minute reminder interval until Done is clicked"}},
              "required": ["title", "kind"]}}
LIST = {"name": "reminder_list", "description": "List active Kepler reminders and their next delivery times.",
        "parameters": {"type": "object", "properties": {}}}
CANCEL = {"name": "reminder_cancel", "description": "Cancel a Kepler reminder by id.",
          "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}


def register(ctx):
    global _store
    _store = Store(plugin_data_dir("kepler-reminders") / "reminders.sqlite3")
    ctx.register_tool(name="reminder_create", toolset="kepler_reminders", schema=CREATE, handler=_create)
    ctx.register_tool(name="reminder_list", toolset="kepler_reminders", schema=LIST, handler=_list)
    ctx.register_tool(name="reminder_cancel", toolset="kepler_reminders", schema=CANCEL, handler=_cancel)
    ctx.register_skill("reminders", Path(__file__).parent / "skills/reminders/SKILL.md")

    def wire(bot, adapter):
        import discord

        global _wake, _loop
        _wake = asyncio.Event()
        channel_id = int(os.environ["KEPLER_REMINDER_CHANNEL_ID"])
        owner_id = int(os.environ["KEPLER_REMINDER_OWNER_ID"])
        worker = None

        def card(row, state="due"):
            spec = row["spec"]
            colors = {"due": 0x3978A8, "done": 0x32856A, "snoozed": 0x9373B3}
            labels = {"due": "ACTION DUE", "done": "ACKNOWLEDGED", "snoozed": "SNOOZED"}
            cadence = spec["kind"].title()
            if spec["kind"] in {"daily", "weekly", "monthly"}:
                scope = ", ".join(spec.get("weekdays", [])) if spec["kind"] == "weekly" else (
                    ", ".join(str(day) for day in spec.get("monthdays", [])) if spec["kind"] == "monthly" else "every day")
                cadence = f"{scope} · {', '.join(spec['times'])} ({spec.get('timezone', 'America/Mexico_City')})"
            if spec.get("repeat_minutes"):
                cadence += f"\nRepeats every {spec['repeat_minutes']} min until Done"
            embed = discord.Embed(title=spec["title"], description=spec.get("details") or None,
                                  color=colors[state], timestamp=datetime.now(timezone.utc))
            embed.set_author(name=f"KEPLER  /  {labels[state]}")
            embed.add_field(name="Schedule", value=cadence, inline=False)
            due = datetime.fromisoformat(row["next_at"])
            if due.year < 9999:
                embed.add_field(name="Due", value=f"<t:{int(due.timestamp())}:F>", inline=True)
            embed.add_field(name="Reference", value=f"`{row['id']}`", inline=True)
            embed.set_footer(text="Done closes this occurrence · Snooze moves its next delivery")
            return embed

        def buttons(ident):
            view = discord.ui.View(timeout=None)
            for label, style, action, emoji in [
                ("Done", discord.ButtonStyle.success, "done", "✓"),
                ("In 1 hour", discord.ButtonStyle.secondary, "snooze_1h", "⏱"),
                ("Tomorrow", discord.ButtonStyle.secondary, "snooze_1d", "↪")]:
                view.add_item(discord.ui.Button(label=label, style=style, emoji=emoji,
                                                custom_id=f"kepler-reminder:{ident}:{action}"))
            return view

        async def run():
            await bot.wait_until_ready()
            while not bot.is_closed():
                try:
                    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
                except Exception:
                    log.exception("Reminder channel unavailable")
                    await asyncio.sleep(30)
                    continue
                for row in _store.due():
                    try:
                        nonce = hashlib.blake2s(f"{row['id']}:{row['next_at']}".encode(), digest_size=8).hexdigest()
                        msg = await channel.send(content=f"<@{owner_id}>", embed=card(row),
                                                 view=buttons(row["id"]),
                                                 nonce=nonce,
                                                 allowed_mentions=discord.AllowedMentions(users=[discord.Object(id=owner_id)]))
                        _store.delivered(row["id"], row["next_at"], msg.id)
                    except Exception:
                        log.exception("Reminder delivery failed: %s", row["id"])
                        await asyncio.sleep(30)
                _wake.clear()
                next_due = _store.next_due()
                timeout = None if next_due is None else max(1, (next_due - datetime.now(timezone.utc)).total_seconds())
                try:
                    await asyncio.wait_for(_wake.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    pass

        async def on_ready():
            nonlocal worker
            global _loop
            _loop = asyncio.get_running_loop()
            if worker is None or worker.done():
                worker = asyncio.create_task(run(), name="kepler-reminders")

        async def on_interaction(interaction):
            data = interaction.data or {}
            custom = data.get("custom_id", "")
            if not custom.startswith("kepler-reminder:"):
                return
            if interaction.user.id != owner_id or interaction.channel_id != channel_id:
                await interaction.response.send_message("Only the reminder owner can use this card.", ephemeral=True)
                return
            try:
                _, ident, action = custom.split(":", 2)
                if action not in {"done", "snooze_1h", "snooze_1d"}:
                    raise ValueError("Unknown action")
                outcome = _store.act(ident, interaction.message.id, action)
                if outcome == "stale":
                    await interaction.response.send_message("This card is no longer current.", ephemeral=True)
                    return
                row = next((r for r in _store.list(False) if r["id"] == ident), None)
                state = "done" if action == "done" else "snoozed"
                await interaction.response.edit_message(content=None, embed=card(row, state), view=None)
                _wake.set()
            except Exception:
                log.exception("Reminder action failed")
                if not interaction.response.is_done():
                    await interaction.response.send_message("Could not update the reminder. Try again.", ephemeral=True)

        bot.add_listener(on_ready, "on_ready")
        bot.add_listener(on_interaction, "on_interaction")
        # Hermes v0.23.4 wires plugin handlers after waiting for Discord READY.
        # Start now when that first event has already passed; later READY events
        # still use the guarded listener above after a reconnect.
        if bot.is_ready():
            asyncio.create_task(on_ready(), name="kepler-reminders-start")

    ctx.register_platform_handler("discord", wire)
