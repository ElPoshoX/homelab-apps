# OpenSpec: KubeVirt for CKA Practice

## Objective

Install KubeVirt on the Talos homelab cluster and create 3 Ubuntu VMs (1 control plane + 2 workers) for kubeadm-based CKA exam practice. VMs are ephemeral — tear down and rebuild as needed.

## Cluster Context

- **Talos Linux v1.13.3**, Kubernetes v1.36.1, kernel 6.18.33-talos
- **7 bare metal nodes** — 3 CPs (4c/12-16GB) + 4 workers (12c/16-32GB)
- **Cilium v1.19.4** — VXLAN tunnel, kube-proxy replacement, Gateway API
- **Longhorn** for storage (iSCSI), but NOT needed for KubeVirt (use containerDisk)
- **Kata Containers 3.31.0** already running — coexists with KubeVirt (both share `/dev/kvm`)
- **ArgoCD** manages apps in this repo via Kustomize (base/ + envs/homelab/)

### Already Satisfied Prerequisites

| Requirement | Status | How |
|-------------|--------|-----|
| `/dev/kvm` | All 7 nodes | KVM built-in to Talos kernel (CONFIG_KVM_AMD=y, CONFIG_KVM_INTEL=y) |
| `/dev/vhost-net` | All 7 nodes | `vhost_net` in `machine.kernel.modules` |
| `/dev/vhost-vsock` | All 7 nodes | `vhost_vsock` in `machine.kernel.modules` |
| `/dev/net/tun` | All 7 nodes | Built-in to Talos kernel |
| `socketLB.hostNamespaceOnly` | Applied | In `components/cilium/values.yaml` — required for VMs to reach K8s services |
| Privileged containers | Enabled | Talos default |
| containerd | Yes | KubeVirt explicitly supports containerd |

**No Talos system extensions needed.** KubeVirt bundles QEMU/libvirt inside its container images.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Talos Cluster (host)                           │
│                                                 │
│  ┌─────────────┐  KubeVirt Operator             │
│  │ virt-operator│  virt-api, virt-controller     │
│  │ virt-handler │  (DaemonSet on all nodes)      │
│  └─────────────┘                                │
│                                                 │
│  ┌──────────────────────────────────────┐       │
│  │  CKA Practice VMs (virt-launcher pods)│      │
│  │                                       │      │
│  │  ┌─────────┐ ┌────────┐ ┌────────┐  │      │
│  │  │ cka-cp  │ │cka-w1  │ │cka-w2  │  │      │
│  │  │ 2c/4Gi  │ │2c/2Gi  │ │2c/2Gi  │  │      │
│  │  │ Ubuntu  │ │Ubuntu  │ │Ubuntu  │  │      │
│  │  │ kubeadm │ │kubeadm │ │kubeadm │  │      │
│  │  └─────────┘ └────────┘ └────────┘  │      │
│  └──────────────────────────────────────┘       │
└─────────────────────────────────────────────────┘
```

## Installation Steps

### Step 1: Install KubeVirt Operator + CR

```bash
# Get latest stable version
KUBEVIRT_VERSION=$(curl -s https://storage.googleapis.com/kubevirt-prow/release/kubevirt/kubevirt/stable.txt)
echo "Installing KubeVirt ${KUBEVIRT_VERSION}"

# Install operator
kubectl apply -f "https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-operator.yaml"

# Install CR (triggers actual deployment)
kubectl apply -f "https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-cr.yaml"

# Wait for deployment
kubectl -n kubevirt wait kv kubevirt --for condition=Available --timeout=300s
```

**No CDI needed.** We use containerDisk (ephemeral OS images from registry).

### Step 2: Install virtctl CLI

```bash
# macOS
brew install virtctl
# Or download from GitHub releases
```

### Step 3: Create CKA Practice VMs

See manifests in `apps/kubevirt/base/`.

## App Structure (follows repo pattern)

```
apps/kubevirt/
├── base/
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── kubevirt-operator.yaml      # Remote URL reference or local copy
│   ├── kubevirt-cr.yaml            # KubeVirt custom resource
│   ├── cka-vms.yaml                # 3 VirtualMachine definitions
│   └── network-policy.yaml
└── envs/
    └── homelab/
        └── kustomization.yaml
```

## VM Specifications

### cka-cp (Control Plane)

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: cka-cp
  namespace: kubevirt
spec:
  running: false  # Start manually when practicing
  template:
    metadata:
      labels:
        app: cka
        role: control-plane
    spec:
      domain:
        cpu:
          cores: 2
        resources:
          requests:
            memory: 4Gi
        devices:
          disks:
            - name: rootdisk
              disk:
                bus: virtio
            - name: cloudinitdisk
              disk:
                bus: virtio
          interfaces:
            - name: default
              masquerade: {}
      networks:
        - name: default
          pod: {}
      volumes:
        - name: rootdisk
          containerDisk:
            image: quay.io/containerdisks/ubuntu:22.04
        - name: cloudinitdisk
          cloudInitNoCloud:
            userData: |
              #cloud-config
              hostname: cka-cp
              user: ubuntu
              password: cka-practice
              chpasswd: { expire: false }
              ssh_pwauth: true
              package_update: true
              packages:
                - curl
                - apt-transport-https
                - ca-certificates
              runcmd:
                - echo "CKA Control Plane ready"
```

### cka-w1, cka-w2 (Workers)

Same as above but:
- `name: cka-w1` / `cka-w2`
- `hostname: cka-w1` / `cka-w2`
- `memory: 2Gi`
- `role: worker`

## Resource Budget

| Component | CPU | RAM |
|-----------|-----|-----|
| KubeVirt control plane (operator, api, controller, handler) | ~130m | ~2.1 Gi |
| cka-cp (virt-launcher + VM) | 2 cores | ~4.1 Gi |
| cka-w1 (virt-launcher + VM) | 2 cores | ~2.1 Gi |
| cka-w2 (virt-launcher + VM) | 2 cores | ~2.1 Gi |
| **Total** | **~6.1 cores** | **~10.4 Gi** |

Worker-4 (12c/32GB) can host everything alone. Or distribute across workers.

## Known Caveats

### 1. K8s 1.36 Compatibility (Medium Risk)

KubeVirt v1.8 is tested against K8s 1.33-1.35. Your cluster runs 1.36.1. KubeVirt v1.9 beta (May 21, 2026) likely supports 1.36. Options:
- Use latest stable (v1.8) — likely works, untested officially
- Use v1.9 beta if stable isn't out yet
- For CKA practice this is acceptable risk

### 2. DNS Resolution in VMs (Low Risk)

Open Cilium issue #37669 — VMs may not resolve via cluster DNS. Workaround: set DNS in cloud-init:

```yaml
cloudInitNoCloud:
  networkData: |
    version: 2
    ethernets:
      enp1s0:
        dhcp4: true
        nameservers:
          addresses:
            - 192.168.5.192  # AdGuard
            - 8.8.8.8        # Fallback
```

### 3. SELinux Detection (Low Risk)

Talos v1.13 runs SELinux in permissive mode. KubeVirt might misdetect. If VMs fail to start with SELinux errors, add to Talos machine config:

```yaml
machine:
  install:
    extraKernelArgs:
      - selinux=0
```

### 4. containerDisk is Ephemeral

VMs lose all changes on restart. This is fine for CKA practice (rebuild cluster each session). If persistence needed later, switch to DataVolume + CDI + Longhorn.

### 5. Kata Containers Coexistence

No conflict. Both use `/dev/kvm` concurrently — KVM supports multi-tenant access. Regular pods use `runc`, Kata pods use `kata` RuntimeClass, KubeVirt VMs use `virt-launcher` with QEMU directly. All independent.

## CKA Practice Workflow

```bash
# Start VMs for practice session
virtctl start cka-cp
virtctl start cka-w1
virtctl start cka-w2

# Wait for VMs to boot (~30-60 seconds)
kubectl get vmi -n kubevirt

# SSH into control plane
virtctl ssh ubuntu@cka-cp -n kubevirt
# Or console access
virtctl console cka-cp -n kubevirt

# Inside VM: install kubeadm, bootstrap cluster
# ... practice CKA tasks ...

# Tear down when done
virtctl stop cka-cp cka-w1 cka-w2

# Full reset (fresh VMs next time — containerDisk is ephemeral)
kubectl delete vmi --all -n kubevirt
```

## CKA Domains Covered

| Domain | Coverage | Notes |
|--------|----------|-------|
| Cluster Architecture | ✅ Full | Real kubeadm cluster with etcd |
| Workloads & Scheduling | ✅ Full | Multi-node, taints, affinity |
| Services & Networking | ✅ Full | Real CNI, DNS, NetworkPolicy |
| Storage | ✅ Full | PV/PVC, StorageClass inside VMs |
| Troubleshooting | ✅ Full | systemd, journalctl, kubelet restart |
| Cluster Maintenance | ✅ Full | etcd backup/restore, kubeadm upgrade, node drain |

This is the most realistic CKA practice environment possible — full systemd, real etcd, real kubeadm lifecycle.

## Networking Considerations

KubeVirt VMs use `masquerade` mode by default — VM gets a private IP, traffic is NAT'd through the pod IP. This is the simplest mode and works with Cilium VXLAN.

For CKA practice, the 3 VMs need to communicate with each other. Options:
- **Pod network (default):** VMs get pod IPs, can reach each other via pod network. Works out of the box.
- **Secondary network (bridge):** For a dedicated practice network. Requires Multus CNI — overkill for CKA.

**Recommendation:** Use default pod networking. VMs communicate via pod IPs assigned by Cilium.

## Files to Create

1. `apps/kubevirt/base/namespace.yaml` — namespace `kubevirt`
2. `apps/kubevirt/base/kubevirt-cr.yaml` — KubeVirt CR with minimal config
3. `apps/kubevirt/base/cka-vms.yaml` — 3 VirtualMachine definitions
4. `apps/kubevirt/base/network-policy.yaml` — allow inter-VM traffic
5. `apps/kubevirt/base/kustomization.yaml` — standard kustomize
6. `apps/kubevirt/envs/homelab/kustomization.yaml` — env overlay

KubeVirt operator manifests: apply via remote URL or ArgoCD with raw manifest URL.

## Verification Checklist

- [ ] `kubectl get kubevirt -n kubevirt` shows `Available`
- [ ] `kubectl get pods -n kubevirt` — all operator pods Running
- [ ] `virtctl start cka-cp` — VM starts, gets pod IP
- [ ] `virtctl console cka-cp` — can access VM console
- [ ] Inside VM: `curl -k https://kubernetes.default.svc:443` — can reach host cluster API (optional)
- [ ] VMs can ping each other via pod IPs
- [ ] `kubeadm init` works inside cka-cp
- [ ] `kubeadm join` works from cka-w1, cka-w2
