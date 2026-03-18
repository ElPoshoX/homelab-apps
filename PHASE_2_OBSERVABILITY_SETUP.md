# Phase 2: Complete Observability Stack Setup

**Status:** ✅ Prometheus, Loki, Promtail, and Grafana components created and ready to deploy

---

## Overview

This guide covers the complete observability stack for your Kubernetes cluster. It consists of four tightly integrated components that work together to provide comprehensive monitoring and logging.

```
┌──────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY STACK                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Metrics Collection & Storage          Log Collection & Query │
│  ┌──────────────────────────┐          ┌──────────────────┐  │
│  │   Prometheus             │          │  Loki            │  │
│  │  (15s scrape interval)   │          │  (Log Aggregator)│  │
│  │  (100Gi storage, 30d ret)│          │  (50Gi storage)  │  │
│  └────────────┬─────────────┘          └────────┬─────────┘  │
│               │                                 │             │
│    ┌──────────┴─────────────┐                  │             │
│    │                         │                  │             │
│    ▼                         ▼                  ▼             │
│  ┌─────────────────┐  ┌────────────────────────────────────┐ │
│  │  Node/Pod Exps  │  │    Promtail (DaemonSet)           │ │
│  │  Kube-Metrics   │  │  • Runs on every node             │ │
│  │  App Metrics    │  │  • Tails container logs           │ │
│  │  (via scrape)   │  │  • Ships to Loki                  │ │
│  └────────────────┘  └────────────────────────────────────┘ │
│         │                         │                          │
│         └─────────────┬───────────┘                          │
│                       │                                      │
│                       ▼                                      │
│             ┌────────────────────┐                           │
│             │    Grafana         │                           │
│             │  • Dashboards      │                           │
│             │  • Alerts          │                           │
│             │  • Logs + Metrics  │                           │
│             └────────────────────┘                           │
│                       │                                      │
│                       ▼                                      │
│            https://grafana.elposhox.dev                      │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. **Prometheus** (Metrics Collection & Storage)

**Path:** `/Users/az/Git-Repos/homelab-apps/apps/prometheus/`

**Purpose:** Time-series database for metrics from your cluster and applications

**Deployment:**
- **StatefulSet** with 1 replica (can scale for HA)
- **Image:** prom/prometheus:v2.50.0
- **Storage:** 100Gi persistent volume (Longhorn)
- **Retention:** 30 days (dev), 90 days (prod)
- **Scrape Interval:** 15 seconds
- **Port:** 9090
- **Domain:** prometheus.elposhox.dev

**Pre-configured Scrape Jobs:**
- Prometheus self-metrics
- Kubernetes API server
- Kubernetes nodes (kubelet)
- Kubernetes pods (dynamic discovery)

**Resources:**
- Dev: 2Gi RAM request / 4Gi limit, 500m CPU request / 2 CPU limit
- Prod: 3Gi RAM request / 6Gi limit, 1 CPU request / 4 CPU limit

**Security:**
- Non-root user (nobody)
- Read-only filesystem
- Dropped capabilities
- Pod Security Standards

---

### 2. **Loki** (Log Aggregation & Querying)

**Path:** `/Users/az/Git-Repos/homelab-apps/apps/loki/`

**Purpose:** Log aggregation system optimized for label-based querying (like Prometheus but for logs)

**Deployment:**
- **StatefulSet** with 1 replica
- **Image:** grafana/loki:3.0.0
- **Storage:** 50Gi persistent volume (Longhorn) for dev, 100Gi for prod
- **Port:** 3100
- **Domain:** loki.elposhox.dev
- **Storage Type:** BoltDB Shipper (local filesystem)

**Key Features:**
- Label-based querying (same labels as Prometheus)
- Log chunking and compression (snappy)
- 1-hour chunk age limit
- Efficient storage via chunking
- Multi-tenancy disabled (single user, perfect for homelab)

**Resources:**
- Dev: 512Mi RAM request / 1Gi limit, 100m CPU request / 500m limit
- Prod: 1Gi RAM request / 2Gi limit, 250m CPU request / 1 CPU limit

---

### 3. **Promtail** (Log Shipping)

**Path:** `/Users/az/Git-Repos/homelab-apps/apps/promtail/`

**Purpose:** Agent that runs on every node and ships container logs to Loki

**Deployment:**
- **DaemonSet** (runs on every node automatically)
- **Image:** grafana/promtail:3.0.0
- **Port:** 3101 (metrics)
- **Privileges:** Runs as root to access node logs

**Log Sources:**
1. **Kubernetes Pods:** Via kubelet API (recommended)
   - Automatically discovers all container logs
   - Adds pod metadata as labels (namespace, pod name, container name)
   - Reads from `/var/log/pods/`

2. **System Logs:** Via syslog
   - Captures `/var/log/syslog`

3. **Kubelet Logs:** Via `/var/log/pods/kube-system_*/`
   - Kubernetes system component logs

**Label Strategy:**
All logs are tagged with:
- `namespace`: Kubernetes namespace
- `pod`: Pod name
- `container`: Container name
- `node`: Node name
- `image`: Container image
- Pod custom labels (auto-extracted)

**Resources:**
- Dev: 64Mi RAM request / 200Mi limit, 50m CPU request / 200m limit
- Prod: 128Mi RAM request / 256Mi limit, 100m CPU request / 500m limit

---

### 4. **Grafana** (Visualization & Alerting)

**Path:** `/Users/az/Git-Repos/homelab-apps/apps/grafana/`

**Purpose:** Unified visualization dashboard for metrics and logs

**Deployment:**
- **Deployment** with 1 replica
- **Image:** grafana/grafana:11.0.0
- **Port:** 3000
- **Domain:** grafana.elposhox.dev

**Default Configuration:**
- **Admin User:** admin
- **Default Password:** grafana123 (⚠️ CHANGE THIS IN PRODUCTION)
- **Plugins:** grafana-piechart-panel

**Pre-configured Datasources:**
1. **Prometheus** (Default)
   - URL: `http://prometheus.prometheus.svc.cluster.local:9090`
   - Query language: PromQL
   - Default datasource for dashboards

2. **Loki**
   - URL: `http://loki.loki.svc.cluster.local:3100`
   - Query language: LogQL
   - For log search and analysis

**Security:**
- Secure cookies enabled
- SameSite=Strict (CSRF protection)
- Non-root user
- No privilege escalation

**Resources:**
- Dev: 256Mi RAM request / 512Mi limit, 100m CPU request / 500m limit
- Prod: 512Mi RAM request / 1Gi limit, 250m CPU request / 1 CPU limit

**Storage:** Uses emptyDir (data lost on pod restart)
- For persistent dashboards: upgrade to PersistentVolumeClaim

---

## Directory Structure

```
/Users/az/Git-Repos/homelab-apps/apps/
├── prometheus/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── prometheus-rbac.yaml
│   │   ├── prometheus-statefulset.yaml
│   │   └── prometheus-service.yaml
│   └── envs/homelab/
│       ├── kustomization.yaml (overrides)
│       ├── ingress.yaml
│       └── rbac-homelab.yaml
│
├── loki/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── loki-rbac.yaml
│   │   └── loki-statefulset.yaml
│   └── envs/homelab/
│       ├── kustomization.yaml (overrides)
│       └── ingress.yaml
│
├── promtail/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── promtail-rbac.yaml
│   │   └── promtail-daemonset.yaml
│   └── envs/homelab/
│       └── kustomization.yaml (overrides)
│
└── grafana/
    ├── base/
    │   ├── kustomization.yaml
    │   ├── namespace.yaml
    │   ├── grafana-rbac.yaml
    │   └── grafana-deployment.yaml
    └── envs/homelab/
        ├── kustomization.yaml (overrides)
        └── ingress.yaml
```

---

## Deployment Instructions

### Step 1: Verify Components Exist

```bash
find /Users/az/Git-Repos/homelab-apps/apps/{prometheus,loki,promtail,grafana} -name "*.yaml" | wc -l
# Should show 25 files
```

### Step 2: Validate Kustomize Configs

```bash
# Validate each component
kustomize build /Users/az/Git-Repos/homelab-apps/apps/prometheus/envs/homelab
kustomize build /Users/az/Git-Repos/homelab-apps/apps/loki/envs/homelab
kustomize build /Users/az/Git-Repos/homelab-apps/apps/promtail/envs/homelab
kustomize build /Users/az/Git-Repos/homelab-apps/apps/grafana/envs/homelab
```

### Step 3: Commit to Git

```bash
cd /Users/az/Git-Repos/homelab-apps
git add apps/prometheus apps/loki apps/promtail apps/grafana
git commit -m "Add complete observability stack (Prometheus, Loki, Promtail, Grafana)

- Prometheus: Metrics collection and time-series storage (100Gi)
- Loki: Log aggregation with label-based querying (50Gi)
- Promtail: Log shipping DaemonSet on all nodes
- Grafana: Unified visualization with pre-configured datasources
- All components follow base/envs/homelab pattern
- Traefik ingress configured for all components

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

### Step 4: ArgoCD Auto-Discovery

ArgoCD's ApplicationSet will automatically detect and deploy:
1. **prometheus-homelab** → prometheus namespace
2. **loki-homelab** → loki namespace
3. **promtail-homelab** → promtail namespace
4. **grafana-homelab** → grafana namespace

Monitor deployment:
```bash
kubectl -n argocd get applications
watch -c kubectl -n argocd get applications
```

### Step 5: Verify Deployment

```bash
# Check all namespaces are created
kubectl get ns | grep -E "prometheus|loki|promtail|grafana"

# Check pods are running
kubectl get pods -n prometheus
kubectl get pods -n loki
kubectl get pods -n promtail
kubectl get pods -n grafana

# Check storage is allocated
kubectl get pvc -n prometheus
kubectl get pvc -n loki

# Check services
kubectl get svc -n prometheus
kubectl get svc -n loki
kubectl get svc -n promtail
kubectl get svc -n grafana

# Check ingress routes
kubectl get ingressroute -n prometheus
kubectl get ingressroute -n loki
kubectl get ingressroute -n grafana
```

### Step 6: Access Services

Once deployed:
```
Prometheus:  https://prometheus.elposhox.dev
Loki:        https://loki.elposhox.dev
Grafana:     https://grafana.elposhox.dev (default: admin/grafana123)
```

---

## Integration Flow

### Metrics Collection Flow

```
Kubernetes Cluster (nodes, pods, services, etc.)
    ↓
Prometheus Scrape Jobs (every 15 seconds)
    ↓
Prometheus TSDB (/prometheus)
    ↓
Grafana Dashboard (queries via PromQL)
```

### Log Collection Flow

```
Container stdout/stderr
    ↓
Kubelet stores in /var/log/pods/*/*.log
    ↓
Promtail DaemonSet (reads every pod's logs)
    ↓
Loki API (http://loki.loki.svc.cluster.local:3100/loki/api/v1/push)
    ↓
Loki Storage (/loki/chunks)
    ↓
Grafana Log Viewer (queries via LogQL)
```

---

## Querying Examples

### Prometheus (PromQL)

```promql
# CPU usage across all nodes
sum(rate(container_cpu_usage_seconds_total[5m])) by (node)

# Memory usage per pod
sum(container_memory_usage_bytes) by (pod_name) / (1024^3)

# Pod restart count
increase(kube_pod_container_status_restarts_total[1h])

# Prometheus ingestion rate
rate(prometheus_tsdb_symbol_table_size_bytes[5m])
```

### Loki (LogQL)

```logql
# All logs from a namespace
{namespace="prometheus"}

# Errors in a pod
{namespace="grafana", pod="grafana-0"} |= "ERROR"

# Logs from a specific container
{namespace="kube-system", container="kubelet"} | json

# Count errors per pod
sum by (pod) (count_over_time({namespace="default"} |= "ERROR" [5m]))

# Average response time from nginx logs
avg_over_time({job="nginx"} | json | duration_ms [5m])
```

---

## Monitoring Recommendations

### Critical Dashboards to Create

1. **Cluster Health Dashboard**
   - Node CPU/Memory/Disk usage
   - Pod count per namespace
   - Container restarts
   - PVC usage

2. **Application Monitoring**
   - Request rate and latency
   - Error rate
   - Resource consumption
   - Custom application metrics

3. **Storage Monitoring**
   - Longhorn volume health
   - PVC usage trends
   - Inode usage
   - I/O performance

4. **Log Analysis**
   - Error rate per application
   - Warning rate per namespace
   - Search logs by error type
   - Pod restart logs

### Alert Rules to Configure

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: homelab-alerts
spec:
  groups:
    - name: kubernetes.rules
      rules:
        - alert: PodRestartingTooOften
          expr: rate(kube_pod_container_status_restarts_total[15m]) > 0.1
          for: 5m
          annotations:
            summary: "Pod {{ $labels.pod }} is restarting too often"

        - alert: HighMemoryUsage
          expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
          for: 5m
          annotations:
            summary: "Pod {{ $labels.pod }} is using >90% memory"

        - alert: DiskSpaceRunningOut
          expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
          for: 5m
          annotations:
            summary: "Node {{ $labels.node }} has <10% disk space"

        - alert: PrometheusDown
          expr: up{job="prometheus"} == 0
          for: 5m
          annotations:
            summary: "Prometheus is down"
```

---

## Troubleshooting

### Prometheus Not Scraping Targets

```bash
# Check Prometheus targets
kubectl port-forward -n prometheus prometheus-0 9090:9090
# Visit: http://localhost:9090/targets

# Check logs
kubectl logs -n prometheus prometheus-0
```

### Loki Storage Full

```bash
# Check storage usage
kubectl exec -n loki loki-0 -- du -sh /loki

# Check PVC status
kubectl get pvc -n loki loki-storage-loki-0 -o yaml

# If full, delete oldest logs (careful!)
kubectl exec -n loki loki-0 -- find /loki/chunks -type d -mtime +7 -exec rm -rf {} \;
```

### Grafana Password Reset

```bash
# Change admin password
kubectl patch secret grafana-admin -n grafana -p '{"data":{"password":"'$(echo -n 'newpassword' | base64)'"}}'

# Restart pod
kubectl rollout restart deployment/grafana -n grafana
```

### Promtail Not Collecting Logs

```bash
# Check Promtail logs
kubectl logs -n promtail -l app.kubernetes.io/name=promtail --tail=50

# Verify Loki is accessible
kubectl exec -n promtail -it -l app.kubernetes.io/name=promtail -- \
  curl -v http://loki.loki.svc.cluster.local:3100/ready

# Check pod discovery
kubectl exec -n promtail -it -l app.kubernetes.io/name=promtail -- \
  grep "kubernetes-pods" /etc/promtail/promtail-config.yaml
```

---

## Performance Tuning

### Prometheus

**Reduce cardinality (if slow):**
```yaml
# In ConfigMap, drop high-cardinality labels
metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'container_.*_bytes'
    action: drop
```

**Increase retention (if disk available):**
```yaml
# In StatefulSet args
- "--storage.tsdb.retention.time=180d"
- "--storage.tsdb.retention.size=500GB"
```

### Loki

**Adjust chunk size (if OOM):**
```yaml
ingester:
  max_chunk_size: 262144  # Reduce from 6291456 for lower memory
```

**Tune retention:**
```yaml
table_manager:
  retention_deletes_enabled: true
  retention_period: 2592000  # 30 days in seconds
```

### Promtail

**Filter unnecessary logs:**
```yaml
scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Drop logs from certain namespaces
      - source_labels: [__meta_kubernetes_namespace]
        regex: 'kube-(system|public|node-lease)'
        action: drop
```

---

## Next Steps

### Immediate (Week 1)
1. ✅ Deploy Prometheus, Loki, Promtail, Grafana
2. ✅ Verify all pods are running
3. ✅ Confirm ingress routes work
4. Create basic dashboards in Grafana

### Short-term (Week 2)
- Add AlertManager for alert routing
- Create PrometheusRule CRDs for critical alerts
- Add Kubernetes dashboard to Grafana
- Set up log retention policies

### Medium-term (Week 3-4)
- Add Cilium for network observability (Hubble)
- Create application-specific dashboards
- Implement alert notifications (Slack, email, PagerDuty)
- Add backup strategy for Prometheus/Loki data

### Long-term
- Migrate to distributed Loki (if data grows)
- Add service mesh observability (Cilium + Hubble)
- Implement trace collection (Jaeger/Tempo)
- Create runbooks for common alerts

---

## References

- **Prometheus Docs:** https://prometheus.io/docs/
- **Grafana Docs:** https://grafana.com/docs/grafana/latest/
- **Loki Docs:** https://grafana.com/docs/loki/latest/
- **Promtail Docs:** https://grafana.com/docs/loki/latest/clients/promtail/
- **Your Repository:** `/Users/az/Git-Repos/homelab-apps/`

---

**Ready to deploy the complete observability stack?** Push to Git and watch ArgoCD deploy it automatically! 🚀

Components are interdependent:
- Prometheus ← metrics source
- Loki ← logs storage
- Promtail ← needs Loki to be ready
- Grafana ← needs Prometheus and Loki to be ready

ArgoCD will handle the ordering automatically!
