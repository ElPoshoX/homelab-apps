# Cilium Gateway HTTPRoute Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert all 13 Traefik IngressRoute resources to Cilium Gateway HTTPRoute resources that reference the shared `homelab-gateway`.

**Architecture:** Extract metadata (hostname, service, port, namespace) from each IngressRoute file, generate HTTPRoute YAML following the approved pattern, validate conversions, then replace files in-place. All routes reference the same `homelab-gateway` in the `ingress` namespace.

**Tech Stack:** Kubernetes Gateway API, Cilium Gateway, YAML

---

## File Mapping

**Files to modify (13 total):**

1. `apps/longhorn-system/base/ingress.yaml`
2. `apps-old/adguard-sync/base/ingress.yaml`
3. `apps-old/adguard/base/ingress.yaml`
4. `apps-old/firefly-iii/base/ingress.yaml`
5. `apps-old/grafana/envs/prd/ingress.yaml`
6. `apps-old/home-assistant/base/ingress.yaml`
7. `apps-old/homepage/base/ingress.yaml`
8. `apps-old/loki/envs/prd/ingress.yaml`
9. `apps-old/longhorn-system/base/ingress.yaml`
10. `apps-old/myspeed/base/ingress.yaml`
11. `apps-old/n8n/base/ingress.yaml`
12. `apps-old/prometheus/envs/prd/ingress.yaml`
13. `apps-old/uptime-kuma/base/ingress.yaml`

**No new files created.** All conversions are in-place replacements.

---

## Task 1: Extract and Validate Ingress Metadata

**Files:**
- Read: All 13 ingress.yaml files

- [ ] **Step 1: Extract metadata from all IngressRoute files**

Create a text file documenting each conversion. For each file, extract:
- File path
- Resource name (metadata.name)
- Namespace (metadata.namespace or default if omitted)
- Hostname (from Host() rule)
- Service name
- Service port
- Labels (if any, preserve in HTTPRoute)

Expected extractions (from reading all files):

```
apps/longhorn-system/base/ingress.yaml
  Name: longhorn
  Namespace: longhorn-system (inferred, check file)
  Hostname: longhorn.elposhox.dev
  Service: longhorn-frontend
  Port: 80

apps-old/adguard-sync/base/ingress.yaml
  Name: adguard-sync
  Namespace: adguard-sync (inferred)
  Hostname: adguard-sync.elposhox.dev
  Service: adguard-sync
  Port: 80

apps-old/adguard/base/ingress.yaml
  Name: adguard
  Namespace: adguard (inferred)
  Hostname: adguard.elposhox.dev
  Service: adguard
  Port: 80

apps-old/firefly-iii/base/ingress.yaml
  Name: firefly-iii
  Namespace: firefly-iii (inferred)
  Hostname: firefly-iii.elposhox.dev
  Service: firefly-iii
  Port: 80

apps-old/grafana/envs/prd/ingress.yaml
  Name: grafana
  Namespace: grafana
  Hostname: grafana.elposhox.dev
  Service: grafana
  Port: 3000

apps-old/home-assistant/base/ingress.yaml
  Name: home-assistant
  Namespace: home-assistant (inferred)
  Hostname: home-assistant.elposhox.dev
  Service: home-assistant
  Port: (extract from file)

apps-old/homepage/base/ingress.yaml
  Name: homepage
  Namespace: (inferred, check file)
  Hostname: home.elposhox.dev
  Service: homepage
  Port: 80

apps-old/loki/envs/prd/ingress.yaml
  Name: loki
  Namespace: loki (inferred)
  Hostname: loki.elposhox.dev
  Service: loki
  Port: (extract from file)

apps-old/longhorn-system/base/ingress.yaml
  Name: longhorn
  Namespace: longhorn-system (inferred)
  Hostname: longhorn.elposhox.dev
  Service: longhorn-frontend
  Port: 80

apps-old/myspeed/base/ingress.yaml
  Name: myspeed
  Namespace: myspeed (inferred)
  Hostname: myspeed.elposhox.dev
  Service: myspeed
  Port: (extract from file)

apps-old/n8n/base/ingress.yaml
  Name: n8n
  Namespace: n8n (inferred)
  Hostname: n8n.elposhox.dev
  Service: n8n
  Port: (extract from file)

apps-old/prometheus/envs/prd/ingress.yaml
  Name: prometheus
  Namespace: prometheus (inferred)
  Hostname: prometheus.elposhox.dev
  Service: prometheus
  Port: (extract from file)

apps-old/uptime-kuma/base/ingress.yaml
  Name: uptime-kuma
  Namespace: uptime-kuma (inferred)
  Hostname: uptime-kuma.elposhox.dev
  Service: uptime-kuma
  Port: (extract from file)
```

- [ ] **Step 2: Read all 13 files and fill in the table**

Verify namespace, service name, and port for each. Document any that don't have explicit namespace in metadata (will need namespace from context/kustomization).

---

## Task 2: Convert apps/longhorn-system/base/ingress.yaml

**Files:**
- Modify: `apps/longhorn-system/base/ingress.yaml`

- [ ] **Step 1: Replace with HTTPRoute**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: longhorn
  namespace: longhorn-system
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - longhorn.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: longhorn-frontend
          port: 80
```

- [ ] **Step 2: Validate YAML syntax**

```bash
kubectl apply -f apps/longhorn-system/base/ingress.yaml --dry-run=client
```

Expected: No errors, output shows HTTPRoute created

- [ ] **Step 3: Commit**

```bash
git add apps/longhorn-system/base/ingress.yaml
git commit -m "feat: convert longhorn ingress to cilium httproute"
```

---

## Task 3: Convert apps-old/adguard-sync/base/ingress.yaml

**Files:**
- Modify: `apps-old/adguard-sync/base/ingress.yaml`

- [ ] **Step 1: Replace with HTTPRoute**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: adguard-sync
  namespace: adguard-sync
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - adguard-sync.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: adguard-sync
          port: 80
```

- [ ] **Step 2: Validate YAML syntax**

```bash
kubectl apply -f apps-old/adguard-sync/base/ingress.yaml --dry-run=client
```

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add apps-old/adguard-sync/base/ingress.yaml
git commit -m "feat: convert adguard-sync ingress to cilium httproute"
```

---

## Task 4: Convert apps-old/adguard/base/ingress.yaml

**Files:**
- Modify: `apps-old/adguard/base/ingress.yaml`

- [ ] **Step 1: Replace with HTTPRoute**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: adguard
  namespace: adguard
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - adguard.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: adguard
          port: 80
```

- [ ] **Step 2: Validate YAML syntax**

```bash
kubectl apply -f apps-old/adguard/base/ingress.yaml --dry-run=client
```

- [ ] **Step 3: Commit**

```bash
git add apps-old/adguard/base/ingress.yaml
git commit -m "feat: convert adguard ingress to cilium httproute"
```

---

## Task 5: Convert apps-old/firefly-iii/base/ingress.yaml

**Files:**
- Modify: `apps-old/firefly-iii/base/ingress.yaml`

- [ ] **Step 1: Replace with HTTPRoute**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: firefly-iii
  namespace: firefly-iii
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - firefly-iii.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: firefly-iii
          port: 80
```

- [ ] **Step 2: Validate YAML syntax**

```bash
kubectl apply -f apps-old/firefly-iii/base/ingress.yaml --dry-run=client
```

- [ ] **Step 3: Commit**

```bash
git add apps-old/firefly-iii/base/ingress.yaml
git commit -m "feat: convert firefly-iii ingress to cilium httproute"
```

---

## Task 6: Convert apps-old/grafana/envs/prd/ingress.yaml

**Files:**
- Modify: `apps-old/grafana/envs/prd/ingress.yaml`

- [ ] **Step 1: Replace with HTTPRoute**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: grafana
  namespace: grafana
  labels:
    app.kubernetes.io/name: grafana
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - grafana.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: grafana
          port: 3000
```

Note: Preserved labels from original. Port is 3000 (not 80).

- [ ] **Step 2: Validate YAML syntax**

```bash
kubectl apply -f apps-old/grafana/envs/prd/ingress.yaml --dry-run=client
```

- [ ] **Step 3: Commit**

```bash
git add apps-old/grafana/envs/prd/ingress.yaml
git commit -m "feat: convert grafana ingress to cilium httproute"
```

---

## Task 7: Convert apps-old/home-assistant/base/ingress.yaml

**Files:**
- Modify: `apps-old/home-assistant/base/ingress.yaml`

- [ ] **Step 1: Read the file to extract exact service name and port**

```bash
cat apps-old/home-assistant/base/ingress.yaml
```

- [ ] **Step 2: Replace with HTTPRoute** (adjust service/port from step 1)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: home-assistant
  namespace: home-assistant
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - home-assistant.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: home-assistant
          port: 80
```

- [ ] **Step 3: Validate YAML syntax**

```bash
kubectl apply -f apps-old/home-assistant/base/ingress.yaml --dry-run=client
```

- [ ] **Step 4: Commit**

```bash
git add apps-old/home-assistant/base/ingress.yaml
git commit -m "feat: convert home-assistant ingress to cilium httproute"
```

---

## Task 8: Convert apps-old/homepage/base/ingress.yaml

**Files:**
- Modify: `apps-old/homepage/base/ingress.yaml`

- [ ] **Step 1: Determine namespace** (check file for explicit namespace or kustomization context)

- [ ] **Step 2: Replace with HTTPRoute**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: homepage
  namespace: homepage
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - home.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: homepage
          port: 80
```

Note: Hostname is `home.elposhox.dev` (not `homepage.elposhox.dev`)

- [ ] **Step 3: Validate YAML syntax**

```bash
kubectl apply -f apps-old/homepage/base/ingress.yaml --dry-run=client
```

- [ ] **Step 4: Commit**

```bash
git add apps-old/homepage/base/ingress.yaml
git commit -m "feat: convert homepage ingress to cilium httproute"
```

---

## Task 9: Convert apps-old/loki/envs/prd/ingress.yaml

**Files:**
- Modify: `apps-old/loki/envs/prd/ingress.yaml`

- [ ] **Step 1: Read the file to extract exact service name and port**

```bash
cat apps-old/loki/envs/prd/ingress.yaml
```

- [ ] **Step 2: Replace with HTTPRoute** (adjust service/port from step 1)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: loki
  namespace: loki
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - loki.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: loki
          port: 3100
```

- [ ] **Step 3: Validate YAML syntax**

```bash
kubectl apply -f apps-old/loki/envs/prd/ingress.yaml --dry-run=client
```

- [ ] **Step 4: Commit**

```bash
git add apps-old/loki/envs/prd/ingress.yaml
git commit -m "feat: convert loki ingress to cilium httproute"
```

---

## Task 10: Convert apps-old/longhorn-system/base/ingress.yaml

**Files:**
- Modify: `apps-old/longhorn-system/base/ingress.yaml`

- [ ] **Step 1: Replace with HTTPRoute**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: longhorn
  namespace: longhorn-system
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - longhorn.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: longhorn-frontend
          port: 80
```

- [ ] **Step 2: Validate YAML syntax**

```bash
kubectl apply -f apps-old/longhorn-system/base/ingress.yaml --dry-run=client
```

- [ ] **Step 3: Commit**

```bash
git add apps-old/longhorn-system/base/ingress.yaml
git commit -m "feat: convert longhorn-system ingress to cilium httproute"
```

---

## Task 11: Convert apps-old/myspeed/base/ingress.yaml

**Files:**
- Modify: `apps-old/myspeed/base/ingress.yaml`

- [ ] **Step 1: Read the file to extract exact service name and port**

```bash
cat apps-old/myspeed/base/ingress.yaml
```

- [ ] **Step 2: Replace with HTTPRoute** (adjust service/port from step 1)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: myspeed
  namespace: myspeed
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - myspeed.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: myspeed
          port: 80
```

- [ ] **Step 3: Validate YAML syntax**

```bash
kubectl apply -f apps-old/myspeed/base/ingress.yaml --dry-run=client
```

- [ ] **Step 4: Commit**

```bash
git add apps-old/myspeed/base/ingress.yaml
git commit -m "feat: convert myspeed ingress to cilium httproute"
```

---

## Task 12: Convert apps-old/n8n/base/ingress.yaml

**Files:**
- Modify: `apps-old/n8n/base/ingress.yaml`

- [ ] **Step 1: Read the file to extract exact service name and port**

```bash
cat apps-old/n8n/base/ingress.yaml
```

- [ ] **Step 2: Replace with HTTPRoute** (adjust service/port from step 1)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: n8n
  namespace: n8n
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - n8n.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: n8n
          port: 5678
```

- [ ] **Step 3: Validate YAML syntax**

```bash
kubectl apply -f apps-old/n8n/base/ingress.yaml --dry-run=client
```

- [ ] **Step 4: Commit**

```bash
git add apps-old/n8n/base/ingress.yaml
git commit -m "feat: convert n8n ingress to cilium httproute"
```

---

## Task 13: Convert apps-old/prometheus/envs/prd/ingress.yaml

**Files:**
- Modify: `apps-old/prometheus/envs/prd/ingress.yaml`

- [ ] **Step 1: Read the file to extract exact service name and port**

```bash
cat apps-old/prometheus/envs/prd/ingress.yaml
```

- [ ] **Step 2: Replace with HTTPRoute** (adjust service/port from step 1)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: prometheus
  namespace: prometheus
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - prometheus.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: prometheus
          port: 9090
```

- [ ] **Step 3: Validate YAML syntax**

```bash
kubectl apply -f apps-old/prometheus/envs/prd/ingress.yaml --dry-run=client
```

- [ ] **Step 4: Commit**

```bash
git add apps-old/prometheus/envs/prd/ingress.yaml
git commit -m "feat: convert prometheus ingress to cilium httproute"
```

---

## Task 14: Convert apps-old/uptime-kuma/base/ingress.yaml

**Files:**
- Modify: `apps-old/uptime-kuma/base/ingress.yaml`

- [ ] **Step 1: Read the file to extract exact service name and port**

```bash
cat apps-old/uptime-kuma/base/ingress.yaml
```

- [ ] **Step 2: Replace with HTTPRoute** (adjust service/port from step 1)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: uptime-kuma
  namespace: uptime-kuma
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - uptime-kuma.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: uptime-kuma
          port: 3001
```

- [ ] **Step 3: Validate YAML syntax**

```bash
kubectl apply -f apps-old/uptime-kuma/base/ingress.yaml --dry-run=client
```

- [ ] **Step 4: Commit**

```bash
git add apps-old/uptime-kuma/base/ingress.yaml
git commit -m "feat: convert uptime-kuma ingress to cilium httproute"
```

---

## Task 15: Final Validation

**Files:**
- Verify all 13 HTTPRoute files

- [ ] **Step 1: Verify all conversions with grep**

```bash
grep -r "kind: HTTPRoute" . --include="*.yaml" | wc -l
```

Expected output: `13`

- [ ] **Step 2: Verify no Traefik IngressRoutes remain**

```bash
grep -r "kind: IngressRoute" . --include="*.yaml" | wc -l
```

Expected output: `0`

- [ ] **Step 3: Verify all HTTPRoutes reference homelab-gateway**

```bash
grep -r "homelab-gateway" . --include="*.yaml" | grep -c "parentRefs" || echo "All gateway refs verified"
```

- [ ] **Step 4: Summary commit**

```bash
git log --oneline | head -15
```

Should show 13 individual conversion commits plus this summary.

---

## Notes for Implementation

- **Port variability:** Most services use port 80, but grafana (3000), n8n (5678), prometheus (9090), loki (3100), uptime-kuma (3001) use custom ports. Read each file carefully.
- **Namespace handling:** Most resources don't explicitly declare namespace in metadata; infer from directory path or look for namespace in kustomization.yaml in the same folder.
- **Label preservation:** Grafana has labels — preserve them in the HTTPRoute metadata.
- **Comments/TLS:** Old Traefik comments and TLS config are removed (TLS handled by gateway).
- **Dry-run validation:** Each `kubectl apply --dry-run=client` verifies YAML syntax without applying.
- **Commit frequently:** One commit per file keeps history clear and allows selective rollback if needed.
