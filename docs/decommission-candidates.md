# Homelab decommission candidates

Requested on 2026-11-24. These applications are marked for removal; this list does not change their deployments.

| Application | Status | Dependency to resolve before removal |
| --- | --- | --- |
| Moltis | Stopped; pending removal | Deployment is scaled to zero. Its local `moltis.db` and SQLite sidecars were removed on 2026-11-24. Other local databases and the `obsidian-vault` CouchDB database remain. |
| OpenHands | Pending removal | Uses Aegis Orchestrator. |
| Phoenix | Pending removal | Confirm whether its PostgreSQL data needs to be retained. |
| Aegis Gateway (LiteLLM and Redis) | Pending removal | Hermes and Aegis Orchestrator still point to LiteLLM; migrate Hermes before removal. |
| Aegis Orchestrator | Pending removal | Moltis and OpenHands point to it; both are also pending removal. |
| Aegis Meridian | Pending removal | LiteLLM points to it for Claude models; it is currently unready because its Claude login has expired. |
| Plane | Pending removal | Confirm whether its PostgreSQL data and Garage access grant need to be retained. Linear is the replacement. |

Do not remove Garage, PostgreSQL, or CouchDB as part of this list. Garage stores observability data and PostgreSQL backups; CouchDB also backs Obsidian LiveSync.

Keep Headroom and NATS. Keep CloudNativePG, which manages the PostgreSQL cluster.

## Investigate replacement

| Application | Status | Investigation |
| --- | --- | --- |
| Vault WebDAV | Keep running | Identify current clients and evaluate a replacement before proposing removal. |
