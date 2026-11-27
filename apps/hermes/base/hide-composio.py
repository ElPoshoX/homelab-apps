"""Build a local Hermes catalog overlay without the unused Composio listing."""

from pathlib import Path

source = Path("/opt/hermes/hermes_cli/plugin_catalog.py")
target = Path("/opt/hermes-patch/plugin_catalog.py")
code = source.read_text()
if "def load_catalog_live(" in code and "def load_catalog(" in code:
    patched = code + '''

# Local homelab catalog policy. Keep upstream catalog updates for every other plugin.
_upstream_load_catalog = load_catalog
_upstream_load_catalog_live = load_catalog_live


def load_catalog(catalog_dir=None):
    return [entry for entry in _upstream_load_catalog(catalog_dir)
            if entry.name != "composio-connections"]


def load_catalog_live():
    return [entry for entry in _upstream_load_catalog_live()
            if entry.name != "composio-connections"]
'''
    try:
        compile(patched, str(target), "exec")
    except SyntaxError:
        print("Hermes catalog overlay is incompatible; keeping the upstream catalog")
    else:
        code = patched
else:
    print("Hermes catalog API changed; keeping the upstream catalog")
target.write_text(code)
