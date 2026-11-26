# OneUptime Deployment

## Overview
OneUptime is deployed via Helm chart in the `oneuptime` namespace.

## External Databases (on TrueNAS)
- PostgreSQL 15: `oneuptime-postgres.elposhox.dev:30200`
- Redis 7.0.12: `oneuptime-redis.elposhox.dev:30201`
- ClickHouse 25.7: `https://oneuptime-clickhouse.elposhox.dev`

All databases use SSL/TLS and are configured in the SOPS-encrypted secret.

## Access
- Web UI: https://uptime.elposhox.dev
- Persistent application state is stored in the external databases. The Helm deployments do not mount a local PVC.

## Deployment
Managed by ArgoCD ApplicationSet: `homelab-appset`

## Secrets
Database credentials are stored in `apps/oneuptime/base/secret.yaml` (SOPS-encrypted).
