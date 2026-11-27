---
name: vault-insights
description: "Extract evidence-backed insights from vault notes."
---

# vault-insights

The mounted Obsidian vault is at `/vault`. Read `/vault/_System/schema.md`, `/vault/_System/tag-taxonomy.md`, and `/vault/_insights.md` before acting. The schema and existing insights page are the source of truth; do not use macOS paths or the unavailable `mcp__vault-az` tools mentioned in older wrappers. Use filesystem operations inside the Docker terminal.

Write only under `/vault/agents/kepler/`. Other agents share this vault: use unique note names, check for an existing target before writing, and write through a temporary file followed by an atomic rename. Preserve frontmatter and Obsidian links. If the canonical workflow requires edits outside `agents/kepler`, prepare the proposed content in `agents/kepler` and report the path; do not bypass NFS permissions.

Calculate note counts, incoming and outgoing wikilinks, dead ends, bridge notes, tag cohesion, growth, and unresolved links. Write the report under `/vault/agents/kepler/` with its sample size and calculation date.
