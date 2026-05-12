# Migration Spec: Prometheus Standalone → kube-prometheus-stack

> **Status:** COMPLETE — all 4 phases executed 2026-05-12
> **Date:** 2026-05-11 (spec) / 2026-05-12 (execution)
> **Reviewed by:** DE pass — 8 corrections applied to original draft
> **Result:** Zero-downtime migration, 3 apps consolidated into 1

---

## 1. Current State

### Apps involved (8 total)

| App | Chart | Version | Namespace | Storage |
|-----|-------|---------|-----------|---------|
| prometheus | prometheus | 28.14.0 | prometheus | 50Gi Longhorn, 15d retention |
| alertmanager | alertmanager | 1.34.0 | alertmanager | 5Gi Longhorn |
| grafana | grafana | 10.5.15 | grafana | 20Gi Longhorn, 2 replicas |
| mimir | mimir-distributed | 6.0.6 | mimir | 50Gi ingester + 10Gi store-gw, S3 Garage |
| loki | loki | 6.55.0 | loki | 30Gi Longhorn, S3 Garage |
| tempo | tempo | 2.0.0 | tempo | 30Gi Longhorn, S3 Garage |
| opentelemetry-collector | opentelemetry-collector | 0.147.1 | otel-collector | none (DaemonSet) |
| kube-state-metrics | kube-state-metrics | 7.2.2 | kube-system | none |

### Issues with current setup
1. **Dual AlertManager**: Prometheus chart has `alertmanager.enabled: true` + standalone alertmanager app. Grafana talks to standalone at `alertmanager.alertmanager.svc:9093`.
2. **kube-state-metrics** has `serviceMonitor.enabled: true` but no Prometheus Operator CRD exists — ServiceMonitor is silently ignored.
3. **No ServiceMonitor/PodMonitor support** — all scraping is via ConfigMap scrape_configs. New apps (CNPG, LiteLLM, etc.) can't use CRD-based monitoring.
4. **No PrometheusRule CRD** — alerting rules must be in static config.
5. **Tempo remote_write broken** — URL `http://prometheus:9090/api/v1/write` cannot resolve. Prometheus server service is `prometheus-server` on port 80 (not `prometheus:9090`). Metrics generator silently fails to write.
6. **prometheus-s3-credentials SopsSecret exists** but nothing in the Prometheus config references S3. Likely unused.

### What MUST be preserved
- All Grafana datasources (Prometheus, Loki, Alertmanager, Tempo)
- All Grafana dashboards (dotdc K8s suite + Node Exporter 1860)
- Grafana admin secret (SopsSecret)
- AlertManager Telegram webhook integration
- AlertManager Telegram bot token (SopsSecret)
- Mimir S3 credentials + full distributed config
- Loki S3 credentials + SingleBinary config
- Tempo S3 credentials + receivers config
- OTel Collector pipelines (traces→Tempo, metrics→Mimir)
- Node Exporter on all nodes (privileged namespace)
- 15-day retention on Prometheus
- 50Gi storage on Longhorn
- All HTTPRoute ingresses (Gateway API)
- Tempo remote_write to Prometheus (currently broken — migration fixes this)

### What can be dropped
- **PushGateway** — enabled in old chart but nothing uses it. kube-prometheus-stack does not include pushgateway subchart (confirmed: feature requests #2030, #4695 closed as stale). Deploy separately only if needed.
- **prometheus-s3-credentials** — unreferenced in Prometheus config.

---

## 2. Target State

### kube-prometheus-stack replaces
- `prometheus` app (standalone chart)
- `alertmanager` app (standalone chart)
- `kube-state-metrics` app (standalone chart)

### kube-prometheus-stack includes
- Prometheus Operator v0.90.1 (CRD controller)
- Prometheus instance (CRD-managed)
- AlertManager instance (CRD-managed)
- kube-state-metrics
- Default recording rules + alerting rules
- ServiceMonitor/PodMonitor/PrometheusRule CRDs

### Telegram integration via AlertmanagerConfig CRD
The standalone chart used env var templates (`{{ .Env.TELEGRAM_BOT_TOKEN }}`). The Prometheus Operator does not support this. Instead, use the `AlertmanagerConfig` CRD with `urlSecret` — references a K8s Secret containing the full webhook URL. The SopsSecret creates this Secret.

### Node Exporter phasing
Node Exporter disabled in kube-prometheus-stack during Phase 1. Old prometheus chart's node-exporter continues on hostPort 9100. Two DaemonSets binding the same hostPort will fail. Enable in kube-prometheus-stack after decommissioning old chart.

### Apps that stay unchanged
- **grafana** — keep separate, disable in kube-prometheus-stack. Update datasource URLs
- **mimir** — unchanged
- **loki** — unchanged
- **tempo** — update remote_write URL (also fixes pre-existing bug)
- **opentelemetry-collector** — unchanged
- **metrics-server** — unchanged

### New app structure

| App dir | ArgoCD app name | Chart | Namespace |
|---------|----------------|-------|-----------|
| `apps/monitoring/` | `monitoring-homelab` | kube-prometheus-stack 85.0.1 | `monitoring` |

Using `monitoring` as directory name (not `kube-prometheus-stack`) to match ApplicationSet `namespace = dirname` convention. `fullnameOverride: monitoring` gives clean service names:
- `monitoring-prometheus.monitoring.svc:9090`
- `monitoring-alertmanager.monitoring.svc:9093`

### Apps to remove (after verification)
- `prometheus` (replaced by kube-prometheus-stack)
- `alertmanager` (replaced by kube-prometheus-stack)
- `kube-state-metrics` (included in kube-prometheus-stack)

---

## 3. Implementation: `apps/monitoring/`

### File structure
```
apps/monitoring/
├── base/
│   ├── kustomization.yaml           # Helm chart + resources
│   ├── namespace.yaml               # monitoring ns (privileged PSS for node-exporter)
│   ├── values.yaml                  # kube-prometheus-stack values
│   ├── ingress.yaml                 # HTTPRoutes — Phase 2 (not in resources yet)
│   ├── alertmanager-telegram.yaml   # AlertmanagerConfig CR — Phase 2
│   └── secret-telegram-url.yaml     # SopsSecret template — needs encryption
└── envs/
    └── homelab/
        └── kustomization.yaml       # References base
```

### Critical values.yaml settings

```yaml
# Without these, Prometheus only selects monitors with helm release labels
serviceMonitorSelectorNilUsesHelmValues: false
podMonitorSelectorNilUsesHelmValues: false
ruleSelectorNilUsesHelmValues: false

# Accept Tempo remote_write
enableRemoteWriteReceiver: true

# Disabled: kustomize renders via helm template, Helm hooks for cert-gen don't execute
admissionWebhooks:
  enabled: false

# Disabled Phase 1: hostPort 9100 conflict with old chart's node-exporter
prometheus-node-exporter:
  enabled: false
```

---

## 4. Datasource URL changes

### Grafana datasources to update
```yaml
# OLD: standalone prometheus
url: http://prometheus-server.prometheus.svc.cluster.local:80

# NEW: kube-prometheus-stack (fullnameOverride: monitoring)
url: http://monitoring-prometheus.monitoring.svc.cluster.local:9090
```

```yaml
# OLD: standalone alertmanager
url: http://alertmanager.alertmanager.svc.cluster.local:9093

# NEW
url: http://monitoring-alertmanager.monitoring.svc.cluster.local:9093
```

### Tempo remote_write to update
```yaml
# OLD (broken — service name wrong, port wrong)
remoteWriteUrl: "http://prometheus:9090/api/v1/write"

# NEW (fixes pre-existing bug)
remoteWriteUrl: "http://monitoring-prometheus.monitoring.svc.cluster.local:9090/api/v1/write"
```

### HTTPRoute ingresses to swap
- `prometheus.elposhox.dev` → `monitoring-prometheus:9090` in `monitoring` namespace
- `alertmanager.elposhox.dev` → `monitoring-alertmanager:9093` in `monitoring` namespace

---

## 5. Secrets migration

| What | Approach |
|------|----------|
| Telegram bot token | New SopsSecret `secret-telegram-url.yaml` → creates Secret `telegram-webhook-url` with full webhook URL. Referenced by AlertmanagerConfig CRD via `urlSecret` |
| prometheus-s3-credentials | **Drop** — unreferenced in Prometheus config |

### Telegram SopsSecret setup
```bash
# 1. Edit secret-telegram-url.yaml: replace <YOUR_TELEGRAM_BOT_TOKEN> with actual token
# 2. Encrypt:
sops --encrypt \
  --age age1wtl5vlup8jkg5q3mwyed4mx5c8fsezqcd8lennp0qkreckfnupeswjlk3q \
  --encrypted-regex '^(data|stringData)$' \
  --in-place apps/monitoring/base/secret-telegram-url.yaml
```

---

## 6. Migration steps (zero-downtime)

### Phase 1: Deploy alongside existing ✅ (app created)
1. ✅ Created `apps/monitoring/` — ArgoCD auto-deploys via ApplicationSet
2. Verify CRDs: `kubectl get crd | grep monitoring.coreos.com` (expect 7+)
3. Verify Prometheus targets: `kubectl port-forward -n monitoring svc/monitoring-prometheus 9090:9090`
4. Verify AlertManager starts: `kubectl get pods -n monitoring -l app.kubernetes.io/name=alertmanager`

### Phase 2: Switch consumers + Telegram
5. Encrypt `secret-telegram-url.yaml` with actual Telegram token
6. Add to `kustomization.yaml` resources: `secret-telegram-url.yaml`, `alertmanager-telegram.yaml`, `ingress.yaml`
7. Remove old HTTPRoutes from `apps/prometheus/base/ingress.yaml` and `apps/alertmanager/base/ingress.yaml` (same commit)
8. Update `apps/grafana/base/values.yaml` datasource URLs:
   - Prometheus: `http://monitoring-prometheus.monitoring.svc.cluster.local:9090`
   - AlertManager: `http://monitoring-alertmanager.monitoring.svc.cluster.local:9093`
9. Update `apps/tempo/base/values.yaml`:
   - `remoteWriteUrl: "http://monitoring-prometheus.monitoring.svc.cluster.local:9090/api/v1/write"`
10. Verify all Grafana dashboards load
11. Verify AlertManager sends test Telegram alert
12. Verify Tempo remote_write metrics appear in new Prometheus

### Phase 3: Enable CRD-based monitoring
13. Enable node-exporter in `apps/monitoring/base/values.yaml`: `prometheus-node-exporter.enabled: true`
14. Disable node-exporter in `apps/prometheus/base/values.yaml`: `nodeExporter.enabled: false`
    (same commit to avoid port conflict gap)
15. Enable PodMonitor in `apps/cnpg-system/base/values.yaml`: `podMonitorEnabled: true`
16. Enable PodMonitor in `apps/aegis-postgres/base/cluster.yaml`: `enablePodMonitor: true`
17. Verify all monitors appear in Prometheus targets

### Phase 4: Decommission old
18. Delete `apps/prometheus/` directory
19. Delete `apps/alertmanager/` directory
20. Delete `apps/kube-state-metrics/` directory
21. ArgoCD prunes old resources automatically (`prune: true`)
22. Delete old PVCs: `kubectl delete pvc -n prometheus --all && kubectl delete pvc -n alertmanager --all`
23. Delete old namespaces: `kubectl delete ns prometheus alertmanager`

---

## 7. Validation checklist

### Phase 1
- [ ] `kubectl get crd | grep monitoring.coreos.com` shows 7+ CRDs
- [ ] Prometheus pod running in monitoring namespace
- [ ] AlertManager pod running in monitoring namespace
- [ ] kube-state-metrics pod running in monitoring namespace
- [ ] Prometheus targets page shows kube-state-metrics, kubelet, apiserver scrapes
- [ ] Old prometheus + alertmanager still running in parallel (no disruption)

### Phase 2
- [ ] AlertManager config shows Telegram receiver (via AlertmanagerConfig CRD)
- [ ] Test alert fires and arrives in Telegram
- [ ] All Grafana dashboards load (K8s views, Node Exporter)
- [ ] Grafana datasource health checks pass (Prometheus, Loki, Alertmanager, Tempo)
- [ ] Tempo remote_write metrics appear in new Prometheus
- [ ] prometheus.elposhox.dev resolves to new Prometheus
- [ ] alertmanager.elposhox.dev resolves to new AlertManager

### Phase 3
- [ ] Node Exporter runs on all 6 nodes (monitoring namespace)
- [ ] CNPG PodMonitor produces postgres metrics
- [ ] kube-state-metrics ServiceMonitor produces metrics

### Phase 4
- [ ] No orphaned PVCs in prometheus/alertmanager namespaces
- [ ] Old namespaces deleted
- [ ] No degraded ArgoCD apps

---

## 8. Rollback plan

If anything breaks:
1. Revert Grafana datasource URLs to old values
2. Revert Tempo remote_write URL
3. Re-enable old apps in homelab-apps (restore deleted directories from git)
4. ArgoCD will resync and restore old stack
5. Delete `apps/monitoring/` directory

Old PVCs with data will still exist until explicitly deleted.

---

## 9. DE Review Notes

### Corrections applied to original draft
1. **PushGateway**: Removed from subcharts — kube-prometheus-stack has no pushgateway subchart (confirmed: GH issues #2030, #4695 closed stale). Nothing in the cluster uses it.
2. **Tempo remote_write**: Identified as pre-existing bug — URL `http://prometheus:9090` cannot resolve (service is `prometheus-server:80`). Migration fixes this.
3. **prometheus-s3-credentials**: Dropped — not referenced anywhere in Prometheus config.
4. **AlertManager Telegram**: Changed from `configSecret` approach to `AlertmanagerConfig` CRD with `urlSecret`. Cleaner: keeps token in a K8s Secret, no need to manage full alertmanager.yaml in a SopsSecret.
5. **Service names**: Changed from `kube-prometheus-stack-prometheus` to `monitoring-prometheus` via `fullnameOverride: monitoring`. Shorter, cleaner.
6. **App directory**: Changed from `apps/kube-prometheus-stack/` to `apps/monitoring/` to match ApplicationSet `namespace = dirname` convention.
7. **Node Exporter phasing**: Added hostPort 9100 conflict handling — disable in new stack during Phase 1, swap in Phase 3 (same commit as disabling old).
8. **Selector nil values**: Added `serviceMonitorSelectorNilUsesHelmValues: false` (and pod/rule equivalents). Without these, Prometheus silently ignores monitors from other namespaces.
