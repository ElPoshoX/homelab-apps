"""Install the reviewed plugin into the persistent Hermes home before gateway start."""

from pathlib import Path
import shutil

import hermes_yaml as yaml

source = Path("/opt/hermes-reminders")
home = Path("/opt/data")
plugin = home / "plugins/kepler-reminders"
skill = plugin / "skills/reminders"
skill.mkdir(parents=True, exist_ok=True)
for name in ("__init__.py", "core.py", "plugin.yaml"):
    shutil.copyfile(source / name, plugin / name)
shutil.copyfile(source / "skill.md", skill / "SKILL.md")

# The existing PVC config is authoritative; patch only the plugin enable list.
config_file = home / "config.yaml"
config = yaml.safe_load(config_file.read_text()) or {}
enabled = config.setdefault("plugins", {}).setdefault("enabled", [])
if "kepler-reminders" not in enabled:
    enabled.append("kepler-reminders")
    temporary = config_file.with_suffix(".yaml.tmp")
    temporary.write_text(yaml.safe_dump(config, sort_keys=False))
    temporary.chmod(config_file.stat().st_mode & 0o777)
    temporary.replace(config_file)
