# Cilium Gateway HTTPRoute Migration Design

**Date:** 2026-03-17
**Scope:** Migrate all Traefik IngressRoute resources to Cilium Gateway HTTPRoute
**Status:** Approved

## Overview

Migrate from Traefik `IngressRoute` to Kubernetes Gateway API `HTTPRoute` resources using the existing `homelab-gateway` (Cilium) in the `ingress` namespace.

**Current State:**
- 13 Traefik IngressRoute resources across `apps/` and `apps-old/` directories
- All use simple hostname-based routing (Host rule only)
- Hostnames like `app.elposhox.dev` routing to respective service on port 80

**Target State:**
- 13 Cilium Gateway HTTPRoute resources
- All reference `homelab-gateway` in `ingress` namespace
- Same hostname → service mapping preserved
- Consistent pattern across all resources

## Conversion Strategy

### Pattern Template

Each IngressRoute converts to an HTTPRoute following this structure:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: <original-name>
  namespace: <original-namespace>
spec:
  parentRefs:
    - name: homelab-gateway
      namespace: ingress
  hostnames:
    - <hostname-from-Host-rule>
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: <service-name>
          port: <service-port>
```

### Conversion Rules

1. **Metadata:**
   - Keep original resource name
   - Preserve original namespace

2. **Gateway Reference:**
   - All routes point to `homelab-gateway` in `ingress` namespace

3. **Hostname:**
   - Extract from Traefik `Host()` rule
   - Map directly to `hostnames` array

4. **Backend:**
   - Extract service name and port
   - All current routes use port 80 (HTTP)
   - Add explicit `port: 80` to backendRefs

### Files to Convert

**apps/ directory (active):**
- `apps/longhorn-system/base/ingress.yaml`

**apps-old/ directory (deprecated but requested):**
- apps-old/adguard-sync/base/ingress.yaml
- apps-old/adguard/base/ingress.yaml
- apps-old/cert-manager/ (if exists)
- apps-old/descheduler-k8s/ (if exists)
- apps-old/firefly-iii/base/ingress.yaml
- apps-old/grafana/envs/homelab/ingress.yaml
- apps-old/home-assistant/base/ingress.yaml
- apps-old/homepage/base/ingress.yaml
- apps-old/loki/envs/homelab/ingress.yaml
- apps-old/myspeed/base/ingress.yaml
- apps-old/n8n/base/ingress.yaml
- apps-old/prometheus/envs/homelab/ingress.yaml
- apps-old/uptime-kuma/base/ingress.yaml

## Implementation Plan

1. **Extract metadata** from all 13 IngressRoute files
2. **Generate** HTTPRoute YAML for each resource
3. **Validate** conversions (hostnames, services, ports)
4. **Replace** files in-place with new HTTPRoute resources
5. **Verify** no orphaned Traefik configurations remain
6. **Commit** changes with descriptive message

## Validation Checklist

- [ ] All 13 files processed
- [ ] No hostname duplicates or conflicts
- [ ] All services exist in target namespaces
- [ ] All ports are valid (all should be 80)
- [ ] File locations preserved
- [ ] No syntax errors in generated YAML
