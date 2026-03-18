# Observability Stack - Quick Start Guide

**TL;DR:** Commit, push, and ArgoCD deploys everything automatically!

---

## 30-Second Deployment

```bash
# Navigate to your homelab-apps repository
cd /Users/az/Git-Repos/homelab-apps

# Stage all observability components
git add apps/prometheus apps/loki apps/promtail apps/grafana

# Commit with a clear message
git commit -m "Add observability stack (Prometheus, Loki, Promtail, Grafana)"

# Push to trigger ArgoCD auto-deployment
git push origin main

# Watch deployment (in another terminal)
watch -c kubectl -n argocd get applications
```

That's it! ArgoCD will:
1. Detect the new applications
2. Create namespaces
3. Deploy all 4 components in correct order
4. Set up ingress routes
5. Allocate storage

---

## Access Your Observability Stack

Once deployed (2-5 minutes):

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **Prometheus** | https://prometheus.elposhox.dev | - |
| **Loki** | https://loki.elposhox.dev | - |
| **Grafana** | https://grafana.elposhox.dev | admin/grafana123 ⚠️ |

---

## Verify Deployment

```bash
# Check all components are running
kubectl get pods -n prometheus
kubectl get pods -n loki
kubectl get pods -n promtail
kubectl get pods -n grafana

# Check storage is allocated
kubectl get pvc -A

# Check applications in ArgoCD
kubectl -n argocd get applications
```

---

## First Steps in Grafana

1. **Login:** admin/grafana123
2. **⚠️ IMPORTANT:** Change password immediately
   - Profile menu → Change password
3. **Verify Datasources:**
   - Configuration → Data Sources
   - Should see "Prometheus" and "Loki"
4. **Create Dashboard:**
   - + New → Dashboard
   - Add a panel with query: `up` (shows all targets)
5. **View Logs:**
   - Explore → Loki
   - Query: `{namespace="default"}`

---

## What Gets Deployed

| Component | Type | Purpose | Status |
|-----------|------|---------|--------|
| **Prometheus** | StatefulSet | Metrics collection (15s interval) | 🟢 Ready |
| **Loki** | StatefulSet | Log aggregation and querying | 🟢 Ready |
| **Promtail** | DaemonSet | Log shipping (runs on all nodes) | 🟢 Ready |
| **Grafana** | Deployment | Visualization and dashboards | 🟢 Ready |

---

## Storage Allocated

- **Prometheus:** 100-200Gi (metrics TSDB)
- **Loki:** 50-100Gi (compressed logs)
- **Promtail:** No persistent storage (stateless)
- **Grafana:** No persistent storage (data in ConfigMaps/Secrets)

All use `longhorn-homelab` StorageClass (provided by Longhorn)

---

## Quick Diagnostics

### Prometheus Not Showing Targets?
```bash
kubectl port-forward -n prometheus prometheus-0 9090:9090
# Visit: http://localhost:9090/targets
# All should be "UP" in green
```

### Loki Not Receiving Logs?
```bash
# Check Promtail is running
kubectl get pods -n promtail

# View Promtail logs
kubectl logs -n promtail -l app.kubernetes.io/name=promtail --tail=20

# Check connectivity to Loki
kubectl exec -it -l app.kubernetes.io/name=promtail -n promtail -- \
  curl -v http://loki.loki.svc.cluster.local:3100/ready
```

### Grafana Dashboard Slow?
```bash
# Check Grafana pod logs
kubectl logs -n grafana deployment/grafana

# Verify datasource connectivity
# In Grafana: Configuration → Data Sources → Test
```

---

## Example Queries

### Prometheus (PromQL)

See CPU usage:
```promql
sum by (pod) (rate(container_cpu_usage_seconds_total[5m]))
```

See memory usage:
```promql
sum by (pod) (container_memory_usage_bytes / 1024^3)
```

### Loki (LogQL)

See all error logs:
```loki
{namespace="default"} |= "ERROR"
```

Count errors per pod:
```loki
sum by (pod) (count_over_time({namespace="default"} |= "ERROR" [5m]))
```

---

## Advanced: Custom Monitoring

### Add Prometheus Scrape Target

Edit: `/Users/az/Git-Repos/homelab-apps/apps/prometheus/base/prometheus-service.yaml`

Add to ConfigMap scrape_configs:
```yaml
- job_name: 'my-app'
  static_configs:
    - targets: ['my-app.default:8080']
```

Then:
```bash
git add apps/prometheus/
git commit -m "Add my-app Prometheus scrape target"
git push
```

### Change Grafana Admin Password

```bash
kubectl patch secret grafana-admin -n grafana \
  -p '{"data":{"password":"'$(echo -n 'mynewpassword' | base64)'"}}'

kubectl rollout restart deployment/grafana -n grafana
```

---

## Storage Management

### Check Storage Usage

```bash
# Prometheus storage
kubectl exec -n prometheus prometheus-0 -- du -sh /prometheus

# Loki storage
kubectl exec -n loki loki-0 -- du -sh /loki
```

### Adjust Retention

**Prometheus retention:**
Edit: `apps/prometheus/envs/prd/kustomization.yaml`
- Find: `--storage.tsdb.retention.time=90d`
- Change to desired retention (e.g., `180d` for 6 months)

**Loki retention:**
Edit: `apps/loki/base/loki-statefulset.yaml`
- Adjust ConfigMap `table_manager.retention_period`

---

## Troubleshooting

### Pod Pending (PVC issue)?
```bash
# Check storage class exists
kubectl get storageclass longhorn-homelab

# Check PVC events
kubectl describe pvc prometheus-storage-prometheus-0 -n prometheus

# Check Longhorn status
kubectl get nodes -L longhorn
```

### Pod CrashLoopBackOff?
```bash
# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check resource limits
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Limits"
```

### Ingress Not Working?
```bash
# Check ingress route
kubectl get ingressroute -n prometheus

# Verify Traefik can reach service
kubectl exec -it -n traefik deployment/traefik -- \
  curl -v http://prometheus.prometheus.svc.cluster.local:9090
```

---

## Next: Create Dashboards

### Basic Kubernetes Cluster Dashboard

In Grafana:
1. New Dashboard
2. Add Panel
3. Data Source: Prometheus
4. Queries:
   ```
   # Panel 1: Node CPU
   sum(rate(container_cpu_usage_seconds_total[5m])) by (node)

   # Panel 2: Node Memory
   sum(container_memory_usage_bytes / (1024^3)) by (node)

   # Panel 3: Pod Count
   count(kube_pod_info)

   # Panel 4: Container Restarts (1h)
   increase(kube_pod_container_status_restarts_total[1h])
   ```

---

## Production Checklist

Before going to production:

- [ ] Change Grafana admin password
- [ ] Increase storage if needed (see Customization section)
- [ ] Configure alert rules (optional)
- [ ] Set up notification channels (Slack, email, etc.)
- [ ] Create backup strategy for metrics data
- [ ] Monitor storage growth trends
- [ ] Document custom dashboards

---

## Support

**Need help?**

1. Check component logs: `kubectl logs -n <namespace> <pod>`
2. Review full guides:
   - `PHASE_2_OBSERVABILITY_SETUP.md` - Complete reference
   - `PHASE_2_PROMETHEUS_SETUP.md` - Prometheus details
3. Check Grafana/Prometheus/Loki official docs

---

**Ready?** `git push` and watch it deploy! 🚀
