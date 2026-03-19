# OneUptime Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate from uptime-kuma to OneUptime Helm chart deployment with external databases on TrueNAS for improved monitoring capabilities and cleaner infrastructure management.

**Architecture:** OneUptime Helm deployment in Kubernetes connects to existing PostgreSQL 15, Redis 7.0.12, and ClickHouse 25.7 services on TrueNAS. All three databases are externally managed, keeping the cluster lightweight. OneUptime uses a 40Gi Longhorn PVC for application storage. Ingress via Cilium Gateway HTTPRoute exposes the service at uptime.elposhox.dev.

**Tech Stack:**
- OneUptime Helm Chart v10.0.34+
- Kubernetes Helm (package management)
- Kustomize (manifest composition)
- SOPS (secrets encryption)
- Longhorn (PVC storage)
- Cilium Gateway (ingress)

---

## File Structure

**Files to create:**
```
apps/oneuptime/
├── base/
│   ├── namespace.yaml              # Oneuptime namespace
│   ├── kustomization.yaml          # Helm chart reference + kustomize config
│   ├── values.yaml                 # Helm values (external DB config)
│   ├── pvc.yaml                    # 40Gi Longhorn PVC for app storage
│   ├── secret.yaml                 # SOPS-encrypted database credentials
│   └── ingress.yaml                # Cilium Gateway HTTPRoute
└── envs/
    └── homelab/
        ├── kustomization.yaml      # Environment-specific kustomization
        └── (no overrides needed for initial deploy)
```

**Files to delete:**
```
apps-old/uptime-kuma/              # Entire directory (replaced by apps/oneuptime)
```

---

## Implementation Tasks

### Task 1: Create OneUptime Directory Structure

**Files:**
- Create: `apps/oneuptime/base/`
- Create: `apps/oneuptime/envs/homelab/`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p apps/oneuptime/base
mkdir -p apps/oneuptime/envs/homelab
```

- [ ] **Step 2: Verify directories exist**

```bash
ls -la apps/oneuptime/
ls -la apps/oneuptime/base/
ls -la apps/oneuptime/envs/homelab/
```

Expected: Both directories created successfully

- [ ] **Step 3: Initialize git tracking (add placeholder if needed)**

```bash
touch apps/oneuptime/base/.gitkeep
touch apps/oneuptime/envs/homelab/.gitkeep
git add apps/oneuptime/
```

---

### Task 2: Create OneUptime Namespace

**Files:**
- Create: `apps/oneuptime/base/namespace.yaml`

- [ ] **Step 1: Write namespace manifest**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: oneuptime
  labels:
    app.kubernetes.io/managed-by: kustomize
    app.kubernetes.io/part-of: oneuptime
    homelab.local/OwnedBy: ElPoshoX
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline
```

Save to: `apps/oneuptime/base/namespace.yaml`

- [ ] **Step 2: Verify file content**

```bash
cat apps/oneuptime/base/namespace.yaml
```

Expected: Namespace manifest with correct labels

- [ ] **Step 3: Commit**

```bash
git add apps/oneuptime/base/namespace.yaml
git commit -m "feat: create oneuptime namespace"
```

---

### Task 3: Create Longhorn PVC for App Storage

**Files:**
- Create: `apps/oneuptime/base/pvc.yaml`

- [ ] **Step 1: Write PVC manifest**

```yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: oneuptime-data
  namespace: oneuptime
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 40Gi
```

Save to: `apps/oneuptime/base/pvc.yaml`

- [ ] **Step 2: Verify file content**

```bash
cat apps/oneuptime/base/pvc.yaml
```

Expected: PVC manifest with 40Gi storage request and Longhorn storage class

- [ ] **Step 3: Commit**

```bash
git add apps/oneuptime/base/pvc.yaml
git commit -m "feat: create 40Gi longhorn pvc for oneuptime"
```

---

### Task 4: Create SOPS-Encrypted Secret for Database Credentials

**Files:**
- Create: `apps/oneuptime/base/secret.yaml`

- [ ] **Step 1: Create unencrypted secret template**

First, create a temporary unencrypted file with your database credentials:

```yaml
apiVersion: isindir.github.com/v1alpha3
kind: SopsSecret
metadata:
  name: oneuptime-secret
  namespace: oneuptime
spec:
  suspend: false
  secretTemplates:
    - name: oneuptime-secret
      stringData:
        # PostgreSQL configuration
        POSTGRES_HOST: "oneuptime-postgres.elposhox.dev"
        POSTGRES_PORT: "30200"
        POSTGRES_DB: "oneuptime"
        POSTGRES_USER: "<your-postgres-username>"
        POSTGRES_PASSWORD: "<your-postgres-password>"

        # Redis configuration
        REDIS_HOST: "oneuptime-redis.elposhox.dev"
        REDIS_PORT: "30201"
        REDIS_PASSWORD: "<your-redis-password>"

        # ClickHouse configuration
        CLICKHOUSE_HOST: "oneuptime-clickhouse.elposhox.dev"
        CLICKHOUSE_PORT: "8123"
        CLICKHOUSE_PROTOCOL: "https"
        CLICKHOUSE_USER: "default"
        CLICKHOUSE_PASSWORD: "<your-clickhouse-password>"
```

**Note:** Replace `<your-postgres-username>`, `<your-postgres-password>`, `<your-redis-password>`, `<your-clickhouse-password>` with your actual credentials.

- [ ] **Step 2: Encrypt the secret with SOPS**

```bash
sops -e apps/oneuptime/base/secret-unencrypted.yaml > apps/oneuptime/base/secret.yaml
```

Expected: Encrypted secret file created

- [ ] **Step 3: Verify encryption worked**

```bash
cat apps/oneuptime/base/secret.yaml | head -20
```

Expected: Output should show encrypted content (ENC[...])

- [ ] **Step 4: Delete unencrypted template**

```bash
rm apps/oneuptime/base/secret-unencrypted.yaml
```

- [ ] **Step 5: Commit encrypted secret**

```bash
git add apps/oneuptime/base/secret.yaml
git commit -m "feat: add sops-encrypted oneuptime database credentials"
```

---

### Task 5: Create Helm Values Configuration

**Files:**
- Create: `apps/oneuptime/base/values.yaml`

- [ ] **Step 1: Write Helm values for external databases**

```yaml
# OneUptime Helm Chart Values - External Database Configuration

# Disable internal PostgreSQL - use external on TrueNAS
postgresql:
  enabled: false

# Disable internal Redis - use external on TrueNAS
redis:
  enabled: false

# Disable internal ClickHouse - use external on TrueNAS
clickhouse:
  enabled: false

# OneUptime Application Configuration
oneuptime:

  # Environment variables from secret
  envFrom:
    - secretRef:
        name: oneuptime-secret

  # Pod security and resource constraints
  securityContext:
    fsGroup: 1000

  containerSecurityContext:
    runAsNonRoot: false
    allowPrivilegeEscalation: false

  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "2Gi"
      cpu: "1000m"

# Storage configuration
persistence:
  enabled: true
  storageClassName: longhorn
  size: 40Gi
  mountPath: /app/data

# Service configuration
service:
  type: ClusterIP
  port: 80
  targetPort: 3000

# Disable Helm ingress - use Cilium Gateway HTTPRoute instead
ingress:
  enabled: false

# Replica configuration
replicaCount: 1

# Image configuration
image:
  repository: oneuptime/oneuptime
  tag: "10.0.34"
  pullPolicy: IfNotPresent

# Node affinity (optional - for homelab)
affinity: {}

# Tolerations (optional)
tolerations: []
```

Save to: `apps/oneuptime/base/values.yaml`

- [ ] **Step 2: Verify file content**

```bash
cat apps/oneuptime/base/values.yaml | head -30
```

Expected: Helm values configuration with external database settings

- [ ] **Step 3: Commit**

```bash
git add apps/oneuptime/base/values.yaml
git commit -m "feat: add oneuptime helm values with external database config"
```

---

### Task 6: Create Cilium Gateway HTTPRoute Ingress

**Files:**
- Create: `apps/oneuptime/base/ingress.yaml`

- [ ] **Step 1: Write HTTPRoute manifest**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: oneuptime
  namespace: oneuptime
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - uptime.elposhox.dev
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: oneuptime
          port: 80
```

Save to: `apps/oneuptime/base/ingress.yaml`

- [ ] **Step 2: Verify file content**

```bash
cat apps/oneuptime/base/ingress.yaml
```

Expected: HTTPRoute manifest with uptime.elposhox.dev hostname

- [ ] **Step 3: Commit**

```bash
git add apps/oneuptime/base/ingress.yaml
git commit -m "feat: create cilium gateway httproute for oneuptime"
```

---

### Task 7: Create Base Kustomization with Helm Integration

**Files:**
- Create: `apps/oneuptime/base/kustomization.yaml`

- [ ] **Step 1: Write Kustomization manifest with Helm chart**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Apply labels to all resources
commonLabels:
  app.kubernetes.io/managed-by: kustomize
  app.kubernetes.io/part-of: oneuptime
  homelab.local/OwnedBy: ElPoshoX

# Namespace for all resources
namespace: oneuptime

# Helm chart as a resource
helmCharts:
  - name: oneuptime
    repo: https://charts.oneuptime.com
    releaseName: oneuptime
    version: "10.0.34"
    valuesFile: values.yaml
    namespace: oneuptime

# Additional Kubernetes resources (non-Helm)
resources:
  - namespace.yaml
  - pvc.yaml
  - ingress.yaml
  - secret.yaml
```

Save to: `apps/oneuptime/base/kustomization.yaml`

- [ ] **Step 2: Verify file content**

```bash
cat apps/oneuptime/base/kustomization.yaml
```

Expected: Kustomization with Helm chart integration and resource references

- [ ] **Step 3: Commit**

```bash
git add apps/oneuptime/base/kustomization.yaml
git commit -m "feat: create base kustomization with oneuptime helm chart"
```

---

### Task 8: Create Environment-Specific Kustomization (homelab)

**Files:**
- Create: `apps/oneuptime/envs/homelab/kustomization.yaml`

- [ ] **Step 1: Write environment kustomization**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Reference the base
bases:
  - ../../base

# Environment-specific patches (if needed in future)
# Currently, no overrides needed for homelab environment
```

Save to: `apps/oneuptime/envs/homelab/kustomization.yaml`

- [ ] **Step 2: Verify file content**

```bash
cat apps/oneuptime/envs/homelab/kustomization.yaml
```

Expected: Minimal kustomization that references base

- [ ] **Step 3: Commit**

```bash
git add apps/oneuptime/envs/homelab/kustomization.yaml
git commit -m "feat: create homelab environment kustomization for oneuptime"
```

---

### Task 9: Delete Old uptime-kuma Directory

**Files:**
- Delete: `apps-old/uptime-kuma/` (entire directory)

- [ ] **Step 1: Remove uptime-kuma directory from git**

```bash
git rm -r apps-old/uptime-kuma/
```

Expected: uptime-kuma directory removed from git staging

- [ ] **Step 2: Verify removal**

```bash
git status | grep uptime-kuma
ls apps-old/uptime-kuma/ 2>&1
```

Expected: Directory no longer exists; git status shows deletion

- [ ] **Step 3: Commit deletion**

```bash
git commit -m "feat: remove deprecated uptime-kuma deployment"
```

---

### Task 10: Verify Complete Directory Structure

**Files:**
- None (verification only)

- [ ] **Step 1: Verify complete structure**

```bash
find apps/oneuptime -type f | sort
```

Expected output:
```
apps/oneuptime/base/ingress.yaml
apps/oneuptime/base/kustomization.yaml
apps/oneuptime/base/namespace.yaml
apps/oneuptime/base/pvc.yaml
apps/oneuptime/base/secret.yaml
apps/oneuptime/base/values.yaml
apps/oneuptime/envs/homelab/kustomization.yaml
```

- [ ] **Step 2: Verify no uptime-kuma remains**

```bash
ls -la apps-old/uptime-kuma/ 2>&1
```

Expected: `ls: cannot access 'apps-old/uptime-kuma/': No such file or directory`

- [ ] **Step 3: View git log to confirm commits**

```bash
git log --oneline -10 | grep -E "(oneuptime|uptime-kuma)"
```

Expected: Shows recent commits for oneuptime creation and uptime-kuma deletion

---

### Task 11: Test Kustomize Build (Dry Run)

**Files:**
- None (verification only)

- [ ] **Step 1: Validate Kustomize build**

```bash
cd apps/oneuptime/envs/homelab
kustomize build . --enable-helm
```

Expected: No errors; should output manifests (will show placeholder for external DBs until credentials are resolved)

- [ ] **Step 2: Check for critical resources**

```bash
kustomize build apps/oneuptime/envs/homelab --enable-helm | grep -E "kind:|name:" | head -20
```

Expected: Output includes Namespace, PVC, HTTPRoute, and Helm chart resources

- [ ] **Step 3: Commit successful validation**

```bash
git commit --allow-empty -m "test: validate oneuptime kustomize build succeeds"
```

---

### Task 12: Document OneUptime Configuration

**Files:**
- Create: `docs/oneuptime-setup.md` (optional, for reference)

- [ ] **Step 1: Create documentation**

```markdown
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
- Storage: 40Gi Longhorn PVC for application data

## Deployment
Managed by ArgoCD ApplicationSet: `homelab-appset`

## Secrets
Database credentials are stored in `apps/oneuptime/base/secret.yaml` (SOPS-encrypted).
```

Save to: `docs/oneuptime-setup.md`

- [ ] **Step 2: Commit documentation**

```bash
git add docs/oneuptime-setup.md
git commit -m "docs: add oneuptime deployment documentation"
```

---

## Summary

This plan creates a complete OneUptime deployment structure with:
- ✅ Directory structure: `apps/oneuptime/base` and `apps/oneuptime/envs/homelab`
- ✅ Namespace configuration
- ✅ 40Gi Longhorn PVC for app storage
- ✅ SOPS-encrypted secrets for database credentials
- ✅ Helm values configured for external databases on TrueNAS
- ✅ Cilium Gateway HTTPRoute ingress
- ✅ Removal of old uptime-kuma deployment
- ✅ Kustomize validation

**Next steps after implementation:**
1. Push commits to git
2. ArgoCD will auto-sync and deploy via ApplicationSet
3. Verify OneUptime pod starts and connects to TrueNAS databases
4. Access at https://uptime.elposhox.dev
