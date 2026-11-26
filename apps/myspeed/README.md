# Go speedtest exporter on the homelab

The Argo CD application keeps the `myspeed` namespace, `myspeed` Service, and `speedtest.elposhox.dev` HTTPRoute. It runs `t0mer/speedtest-exporter` v2026.5.2, using the built-in Go engine every two hours. Results, runtime settings, and encrypted notification channels live in SQLite on the `speedtest-exporter-data` Longhorn PVC.

The previous `myspeed-config` and `speedtest-tracker-config` PVCs remain declared but unmounted. Their database schemas are incompatible with the Go exporter. Preserve them for rollback until the old results are no longer needed.

The ServiceMonitor scrapes `/metrics` every minute. Prometheus forwards only `speedtest_*` series to local Mimir, and the provisioned Grafana dashboard uses Mimir. Mimir retains about 31 days of samples; the application's SQLite database retains the full result history. The Go engine does not measure packet loss, so the dashboard intentionally omits packet loss.

The exporter has no built-in authentication. Its hostname resolves to the homelab's private gateway address. Keep the route on the trusted LAN; do not publish it through a public tunnel without adding authentication. Its API includes settings changes, test runs, and unencrypted settings export.

The `#speed-tests` Discord notification channel is configured through the exporter's API and stored encrypted in its SQLite database. Keep its Discord webhook in the encrypted GitOps secret so the channel can be restored if the PVC is lost.

For rollback, restore the previous Speedtest Tracker Deployment, Service, ServiceMonitor, alert, and dashboard manifests from Git, and remount `speedtest-tracker-config`. Keep the new PVC until its results are no longer needed.
