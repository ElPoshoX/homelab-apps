"""Emit a daily Discord reminder after 300 days, resetting on PAT rotation."""

import argparse
import fcntl
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path("/opt/data")
ENV_FILE = HOME / ".env"
STATE_FILE = HOME / "cron/github-token-reminder.json"
LOCK_FILE = HOME / "cron/github-token-reminder.lock"
REMIND_AFTER = timedelta(days=300)
EXPIRY_MARGIN = timedelta(days=30)


def current_token():
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("MCP_GITHUB_API_KEY="):
            return line.partition("=")[2].strip()
    raise RuntimeError("GitHub MCP token is not configured")


def token_expiry(token):
    request = urllib.request.Request(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "KeplerTokenReminder/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            value = response.headers.get("GitHub-Authentication-Token-Expiration")
            return (datetime.strptime(value, "%Y-%m-%d %H:%M:%S UTC")
                    .replace(tzinfo=timezone.utc) if value else None), False
    except urllib.error.HTTPError as error:
        return None, error.code == 401
    except (OSError, TimeoutError, ValueError):
        return None, False


def write_state(state):
    temporary = STATE_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, sort_keys=True) + "\n")
    temporary.chmod(0o600)
    # kubectl exec may run this check as root; keep the PVC owner's access.
    if os.geteuid() == 0:
        owner = HOME.stat()
        os.chown(temporary, owner.st_uid, owner.st_gid)
    temporary.replace(STATE_FILE)


def run(seed=False, now=None):
    now = now or datetime.now(timezone.utc)
    token = current_token()
    fingerprint = hashlib.sha256(token.encode()).hexdigest()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
        rotated = state.get("fingerprint") != fingerprint
        if rotated:
            state = {"fingerprint": fingerprint, "rotated_at": now.isoformat()}

        expiry, invalid = token_expiry(token)
        if expiry:
            state["expires_at"] = expiry.isoformat()
        write_state(state)
        if seed:
            return ""

        rotated_at = datetime.fromisoformat(state["rotated_at"])
        remind_at = rotated_at + REMIND_AFTER
        if state.get("expires_at"):
            expires_at = datetime.fromisoformat(state["expires_at"])
            remind_at = min(remind_at, expires_at - EXPIRY_MARGIN)
        if now < remind_at and not invalid:
            return ""

        remaining = "unknown"
        if state.get("expires_at"):
            remaining = str(max(0, (datetime.fromisoformat(state["expires_at"]) - now).days))
        reason = ("GitHub rejected the current token." if invalid else
                  "The token has entered its renewal window.")
        return ("<@1261063491540746291> 🔐 **Kepler · GitHub token renewal**\n"
                f"{reason} Access: `ElPoshoX` · Days until expiry: **{remaining}**.\n"
                "Create a replacement fine-grained PAT for this organization and update the "
                "encrypted GitOps secret. Do not post the token in Discord.\n"
                "This reminder repeats daily until the token changes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="Record a new token without sending a reminder")
    args = parser.parse_args()
    message = run(seed=args.seed)
    if message:
        print(message)
