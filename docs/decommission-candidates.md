# Homelab service decommission

Completed on 2026-11-24 through GitOps commit `4de54b5` and Argo CD reconciliation.

Removed applications: Aegis Gateway (including LiteLLM and Redis), Aegis Orchestrator,
Aegis Meridian, Moltis, OpenHands, Phoenix, Plane, and Pushgateway. Their GitOps
manifests, application resources, namespaces, and dedicated persistent volumes were
removed. The obsolete `moltis-secured` namespace and five retained Moltis volumes
were also deleted. Moltis's local SQLite database was removed before its deployment
was stopped.

The dedicated PostgreSQL databases `litellm`, `phoenix`, `plane`, and `langgraph`
and the `litellm` and `plane` roles were dropped. The shared PostgreSQL cluster,
Garage, and CouchDB remain. CouchDB's `obsidian-vault` database was not touched.

Headroom, NATS, and CloudNativePG remain in service. Hermes remains installed,
with its retired LiteLLM dependency removed; its model provider still needs
configuration before investigation workflows can use it.

## Pending decisions

- Keep Vault WebDAV running while identifying its clients and evaluating a replacement.
- Decide on Gatus after reviewing the full alert, status page, Hermes investigation,
  and Discord update flow.
