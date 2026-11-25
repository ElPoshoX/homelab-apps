# Homelab decommission candidates

Requested on 2026-11-24. These applications are marked for removal; this list does not change their deployments.

| Application | Status | Dependency to resolve before removal |
| --- | --- | --- |
| Moltis | Pending removal | Uses Aegis Orchestrator and CouchDB; CouchDB also serves Obsidian LiveSync. |
| OpenHands | Pending removal | Uses Aegis Orchestrator. |
| Phoenix | Pending removal | Confirm whether its PostgreSQL data needs to be retained. |
| LiteLLM (Aegis Gateway) | Pending removal | Hermes and Aegis Orchestrator still point to LiteLLM; migrate or remove those callers first. Meridian supplies Claude models through LiteLLM. |
| Plane | Pending removal | Confirm whether its PostgreSQL data and Garage access grant need to be retained. Linear is the replacement. |

Do not remove Garage, PostgreSQL, or CouchDB as part of this list. Garage stores observability data and PostgreSQL backups; CouchDB also backs Obsidian LiveSync.
