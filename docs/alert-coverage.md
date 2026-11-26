# Homelab alert coverage

Prometheus evaluates `PrometheusRule` resources from every namespace. Alertmanager sends firing and resolved notifications to Discord. The `kube-prometheus-stack` default rules cover Kubernetes workloads, nodes, PVC capacity, Jobs, the API server, etcd, Prometheus, Alertmanager, and scrape targets. Application rules live beside the application manifests; shared platform rules live in `apps/monitoring/base`.

## Application inventory

| Application | Alert source | Additional application signal |
| --- | --- | --- |
| AdGuard, AdGuard Sync | Kubernetes workload and PVC rules | DNS query success is not exported to Prometheus. |
| CloudBeaver, CouchDB | Kubernetes workload and PVC rules | No application metrics endpoint is configured. |
| CloudNativePG operator | Kubernetes workload rules; operator PodMonitor | PostgreSQL data-plane rules live with `postgres`. |
| Descheduler | Kubernetes Job rules | `KubeJobFailed` and `KubeJobNotCompleted` cover its CronJob. |
| Garage | Kubernetes workload and PVC rules; Garage PodMonitor | Replica health, RPC timeouts, and storage capacity. |
| Grafana | Kubernetes workload rules | Grafana alerting is not used as the homelab rule owner. |
| Headroom, Hermes, Homepage | Kubernetes workload and PVC rules | No stable application-level Prometheus signal is configured. |
| Loki | Kubernetes workload and PVC rules; Loki ServiceMonitor | WAL data loss and API errors. |
| Longhorn | Kubernetes workload rules; Longhorn PodMonitor | Faulted/degraded volumes, disk readiness, and stale backups. |
| Metrics Server | Kubernetes workload rules | API availability is covered by cluster rules. |
| Mimir | Kubernetes workload and PVC rules; Mimir PodMonitor | Rejected ingestion and ingester ring membership. |
| MySpeed | Kubernetes workload and PVC rules | Speed tests are checked through the application, not a Prometheus exporter. |
| NATS | Kubernetes workload and PVC rules | Its `/varz` monitoring API is not Prometheus format; no exporter is installed. |
| Officina | Kubernetes workload and PVC rules | The health port is not a Prometheus metrics endpoint. |
| OneUptime | Kubernetes workload rules | Synthetic checks and status-page state are owned by OneUptime. |
| OpenTelemetry Collector | Kubernetes DaemonSet rules; chart PodMonitor | Refused telemetry. |
| PostgreSQL | Kubernetes workload and PVC rules; CNPG PodMonitor | Replication, disk capacity, and WAL archiving. |
| Tempo | Kubernetes workload and PVC rules; chart ServiceMonitor | Failed trace flushes. |
| Vault WebDAV | Kubernetes workload and PVC rules | No application metrics endpoint is configured. |

The empty `phoenix` and `pushgateway` directories have no active Argo CD application.

## Shared infrastructure

Talos/Kubernetes nodes, control plane, etcd, CoreDNS, Cilium, ingress, and CSI workloads inherit the stack's node, API, DNS, workload, storage, and scrape-target rules. The platform rule set additionally watches the ingress wildcard TLS certificate through cert-manager metrics. Longhorn-specific storage integrity is kept with Longhorn.

Availability of a pod is not the same as success of an HTTP, DNS, or S3 operation. Synthetic checks remain in OneUptime. Services without application metrics retain workload-level alerting; add a domain rule only when a measurable signal and response action exist.
