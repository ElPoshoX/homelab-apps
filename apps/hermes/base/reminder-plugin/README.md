# Kepler reminders

Hermes plugin for owner-only Discord reminder cards. The gateway's existing Discord bot sends embeds and handles button interactions. No model call is made when a reminder fires or a button is clicked.

The deployment init container copies the plugin into `/opt/data/plugins/kepler-reminders` and enables it in the existing PVC config. State is stored in `/opt/data/plugin-data/kepler-reminders/reminders.sqlite3` on the Hermes PVC. The selected Discord destination is `#reminders`; the owner ID is configured on the gateway container.

## Supported schedules

- One timestamp (`once`)
- Daily, weekly, and monthly local times, including multiple times in a day
- Explicit dates (`dates`)
- Optional repeat interval until the owner presses **Done**

Cards offer **Done**, **In 1 hour**, and **Tomorrow**. Only the configured Discord user can act, and old cards are rejected after a newer delivery. Missing days such as February 31 are skipped. Nonexistent local times during a DST jump are skipped.

## Verify before retiring a legacy reminder

Run `python3 -m unittest discover -s apps/hermes/base/reminder-plugin -p 'test_*.py' -v` and `kubectl kustomize apps/hermes/base`. After rollout, check `hermes plugins doctor kepler-reminders --ci`, create a short one-shot reminder, verify its Discord card, restart Hermes, then verify **Done** and **Snooze**. The existing GitHub PAT renewal cron remains active until this end-to-end check passes and its token-rotation reset behavior is migrated.

Delivery is at least once. A gateway crash after Discord accepts a message but before SQLite records its message ID can create one duplicate on restart. The stable Discord nonce is included to aid reconciliation, but discord.py does not request server-side nonce enforcement.
