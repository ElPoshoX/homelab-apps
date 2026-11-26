# OneUptime ClickHouse upgrade preparation

Prepared on 2026-11-25. This runbook does not deploy the upgrade.

## Current state and target

- TrueNAS SCALE 25.04.2.6 runs the Portainer stack `oneuptime-clickhouse`.
- The stack uses `clickhouse/clickhouse-server:25.7`; the server reports `25.7.8.71`.
- Target: `clickhouse/clickhouse-server:26.11.2.4`, the latest upstream stable release observed on 2026-11-25. Pin this exact tag, not `latest`.
- The container bind-mounts `/mnt/HomeLab/OneUptime/ClickHouse/data` and `/mnt/HomeLab/OneUptime/ClickHouse/logs` from the TrueNAS dataset `HomeLab/OneUptime/ClickHouse`. Ports 30202 and 30203 are published for HTTP and native traffic.
- The `oneuptime` database currently has 24 tables and no active data parts. The ClickHouse `system` database has about 19.44 GiB of active parts, mostly `text_log`, `trace_log`, `metric_log`, and `asynchronous_metric_log`. These log tables contain data back to 2026-03-18 and have no TTL. Recheck immediately before upgrading.
- OneUptime 10.5.29 requires ClickHouse at startup and writes monitor logs there. The OpenTelemetry Collector sends general traces, metrics, and logs to Tempo, Mimir, and Loki; it does not send them to OneUptime.

## Upgrade gate

1. Confirm the exact image tag still exists and review upstream release notes and compatibility changes from 25.7 through 26.11. Test the target image against a copy of this dataset before touching the live stack.
2. Record `SELECT version()`, the tables in `oneuptime`, active part counts and sizes, and the current Portainer stack definition. Preserve the current `25.7` image and configuration for rollback.
3. Take a verified backup of the `oneuptime` database and a TrueNAS snapshot of `HomeLab/OneUptime/ClickHouse` after stopping the ClickHouse container. The snapshot must include the bind-mounted `data` and `logs` directories. Verify the snapshot exists before changing the stack.
4. Change only the image in the Portainer stack `oneuptime-clickhouse` to `clickhouse/clickhouse-server:26.11.2.4`; retain mounts, ports, credentials, and health check. Expect a brief OneUptime outage while ClickHouse restarts.
5. Require a healthy container, `/ping` HTTP 200, `SELECT version()` returning `26.11.2.4`, unchanged `oneuptime` schema and data counts, OneUptime pods Ready, and HTTP 200 from `/dashboard/` and `/status-page/`. Exercise one monitor and incident lifecycle before declaring success.
6. If validation fails, stop the new container, restore the pre-upgrade TrueNAS snapshot, and redeploy the preserved `25.7` stack definition. Do not start 25.7 against data already opened by 26.11 without restoring the snapshot.

## Storage follow-up

The large `system` log tables are ClickHouse's own diagnostics, not OneUptime monitor data. After the upgrade, configure a seven-day TTL for verbose system logs in ClickHouse configuration and verify disk use falls. ClickHouse may preserve the old tables under renamed names when their TTL configuration changes; inspect and remove those only after the new tables and backup are verified. Keep OneUptime's required ClickHouse database; LGTM does not replace it in OneUptime 10.5.29.

## References

- [ClickHouse 26.11.2.4 release](https://github.com/ClickHouse/ClickHouse/releases/tag/v26.11.2.4-stable)
- [ClickHouse packages](https://packages.clickhouse.com/)
- [OneUptime 10.5.29 startup dependency](https://github.com/OneUptime/oneuptime/blob/10.5.29/App/Index.ts)
