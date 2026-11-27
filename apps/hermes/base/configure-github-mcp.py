"""Configure the scoped GitHub MCP credential in each persistent Hermes profile."""

import os
from pathlib import Path

import hermes_yaml as yaml

TOKEN = os.environ["GITHUB_MCP_TOKEN"].strip()
if not TOKEN or any(char.isspace() for char in TOKEN):
    raise SystemExit("GitHub MCP token is missing or malformed")

HOME = Path("/opt/data")
PROFILES = [HOME, *sorted((HOME / "profiles").iterdir())]
SERVER = {
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": {"Authorization": "Bearer ${MCP_GITHUB_API_KEY}"},
    "enabled": True,
}

for profile in PROFILES:
    config_file = profile / "config.yaml"
    if not config_file.is_file():
        continue
    config = yaml.safe_load(config_file.read_text()) or {}
    servers = config.setdefault("mcp_servers", {})
    if servers.get("github") != SERVER:
        servers["github"] = SERVER
        replacement = config_file.with_suffix(".yaml.tmp")
        replacement.write_text(yaml.safe_dump(config, sort_keys=False))
        replacement.chmod(config_file.stat().st_mode & 0o777)
        replacement.replace(config_file)

    env_file = profile / ".env"
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    lines = [line for line in lines if not line.startswith("MCP_GITHUB_API_KEY=")]
    lines.append(f"MCP_GITHUB_API_KEY={TOKEN}")
    replacement = profile / ".env.tmp"
    replacement.write_text("\n".join(lines) + "\n")
    replacement.chmod(0o600)
    replacement.replace(env_file)
    print(f"Configured GitHub MCP for {profile.name}")
