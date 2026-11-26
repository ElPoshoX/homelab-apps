# Speedtest Tracker on the homelab

The Argo CD application keeps the `myspeed` namespace, `myspeed` Service, and `speedtest.elposhox.dev` HTTPRoute. It runs Speedtest Tracker v1.15.1 with a new SQLite database on `speedtest-tracker-config`. Tests run every two hours.

The old `myspeed-config` PVC remains declared but unmounted. MySpeed and Speedtest Tracker have incompatible database schemas, so historical MySpeed results are retained for rollback rather than mounted into the new application. Do not delete that PVC until the old data is no longer needed.

The application key and initial admin password are encrypted in `base/secret.yaml`. The initial login email is `admin@elposhox.dev`. The password is only used on first initialization and can be retrieved with `sops -d base/secret.yaml` by an operator with the age key.

The `postStart` bootstrap enables the application's native `/prometheus` endpoint after database migrations. The ServiceMonitor scrapes it every minute. Prometheus forwards only `speedtest_tracker_*` metrics to local Mimir, and the Grafana dashboard uses the Mimir datasource. Mimir currently retains about 31 days of samples; the SQLite volume retains the application's full result history.

For rollback, restore the previous MySpeed Deployment manifest from Git, point the `myspeed` Service back at its pods, mount `myspeed-config` at `/config`, and restore target port 5216. Keep the new PVC until its results are no longer needed.
