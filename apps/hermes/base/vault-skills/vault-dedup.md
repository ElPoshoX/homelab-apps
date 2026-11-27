---
name: vault-dedup
description: "Detect and resolve duplicate vault notes."
---

# vault-dedup

The mounted Obsidian vault is at `/vault`. Read `/vault/_System/schema.md`, `/vault/_System/tag-taxonomy.md`, and `/vault/_System/skills/wiki-dedup.md` before acting. These files are the source of truth; do not use macOS paths or the unavailable `mcp__vault-az` tools mentioned in older wrappers. Use filesystem operations inside the Docker terminal.

Write only under `/vault/agents/kepler/`. Other agents share this vault: use unique note names, check for an existing target before writing, and write through a temporary file followed by an atomic rename. Preserve frontmatter and Obsidian links. If the canonical workflow requires edits outside `agents/kepler`, prepare the proposed content in `agents/kepler` and report the path; do not bypass NFS permissions.
