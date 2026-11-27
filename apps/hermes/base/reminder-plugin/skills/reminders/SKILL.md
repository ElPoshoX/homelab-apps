---
name: reminders
description: Create, inspect, and cancel durable Kepler reminders delivered to Discord.
---

# Reminders

Use `reminder_create` for requests to be reminded. Ask for a date only when the user has not supplied enough information to calculate one. Use `America/Mexico_City` unless the user specifies another timezone.

- `once`: pass `at` as an ISO 8601 timestamp with an offset.
- `daily`: pass one or more local `times` as `HH:MM`.
- `weekly`: pass `weekdays` (`mon` through `sun`) and `times`.
- `monthly`: pass `monthdays` (1–31) and `times`; missing days in short months are skipped.
- `dates`: pass an explicit list of ISO 8601 timestamps with offsets.
- For “keep reminding me until I acknowledge it,” set `repeat_minutes`. Otherwise each scheduled occurrence is delivered once.

The owner can use **Done**, **In 1 hour**, or **Tomorrow** on the Discord card. Use `reminder_list` to check the next delivery and `reminder_cancel` to stop a reminder. Never claim that a reminder was created until the tool returns its ID.
