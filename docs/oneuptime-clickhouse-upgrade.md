# OneUptime ClickHouse upgrade

Prepared on 2026-11-25 and deployed on 2026-11-26 UTC.

## Deployment result

- Stopped the old ClickHouse container and verified TrueNAS snapshot `HomeLab/OneUptime/ClickHouse@pre-clickhouse-26-11-20261126-015311` before the stack update.
- Updated Portainer stack `oneuptime-clickhouse` (ID 45, endpoint 4) from image `clickhouse/clickhouse-server:25.7` to `clickhouse/clickhouse-server:26.11.2.4`. Its other stack settings were preserved.
- The new container reported healthy, `/ping` returned HTTP 200, and `SELECT version()` returned `26.11.2.4`. The `oneuptime` database retained 24 tables and zero active parts, matching the pre-upgrade baseline.
- All four OneUptime pods were Ready, Argo CD reported `oneuptime-homelab` Synced/Healthy, and `https://uptime.elposhox.dev/dashboard/` and `/status-page/` returned HTTP 200. The application log reported `Clickhouse is connected` and `Live check: ok` after the restart.
- On 2026-11-26 UTC, a controlled failure of the Speedtest monitor moved it from Operational to Offline and created an automatic incident. Restoring the original destination and interval caused the next probe check to return the monitor to Operational and automatically resolve the incident. The original monitor configuration was verified after restoration.
- This test uncovered that the monitor's three assigned probes had been disconnected since March 2026. The currently connected probe was assigned to the monitor and completed both test checks. Probe assignment needs a durable fix across future probe replacements; the chart-rendered probe key differs from the key used by the running probe.
- The incident was marked visible on the status page, but the public page is a client-rendered application and its visible rendering was not verified. No Discord workspace notification channel or status-page subscribers are configured, so alert delivery to Discord was not verified.

## Current state and target

- TrueNAS SCALE 25.04.2.6 runs the Portainer stack `oneuptime-clickhouse`.
- Before the upgrade, the stack used `clickhouse/clickhouse-server:25.7` and the server reported `25.7.8.71`.
- Deployed image: `clickhouse/clickhouse-server:26.11.2.4`, the latest upstream stable release observed on 2026-11-25. Keep this exact tag pinned.
- The container bind-mounts `/mnt/HomeLab/OneUptime/ClickHouse/data` and `/mnt/HomeLab/OneUptime/ClickHouse/logs` from the TrueNAS dataset `HomeLab/OneUptime/ClickHouse`. Ports 30202 and 30203 are published for HTTP and native traffic.
- At the pre-upgrade check, the `oneuptime` database had 24 tables and no active data parts. The ClickHouse `system` database had about 19.44 GiB of active parts, mostly `text_log`, `trace_log`, `metric_log`, and `asynchronous_metric_log`. These log tables contain data back to 2026-03-18 and have no TTL.
- OneUptime 10.5.29 requires ClickHouse at startup and writes monitor logs there. The OpenTelemetry Collector sends general traces, metrics, and logs to Tempo, Mimir, and Loki; it does not send them to OneUptime.

## Procedure and rollback

The production change used steps 2–5 below. A test against a copy of the dataset was not performed. The controlled monitor and incident lifecycle was verified after the upgrade, with notification delivery still open.

1. Confirm the exact image tag still exists and review upstream release notes and compatibility changes from 25.7 through 26.11. For future major upgrades, test the target image against a copy of the dataset before touching the live stack.
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
