#!/bin/bash

##############################################################################
# Observability Stack Validation Script
#
# Validates all components are present and correctly configured
# before deployment via ArgoCD
#
# Usage: ./hack/validate-observability-stack.sh
##############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Observability Stack Validation Script                     ║${NC}"
echo -e "${BLUE}║  Validates: Prometheus, Loki, Promtail, Grafana           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
COMPONENTS=("prometheus" "loki" "promtail" "grafana")
REQUIRED_FILES=("base/kustomization.yaml" "base/namespace.yaml" "envs/prd/kustomization.yaml")
ERRORS=0
WARNINGS=0

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    local status=$1
    local message=$2

    if [[ $status -eq 0 ]]; then
        echo -e "${GREEN}✓${NC} $message"
    else
        echo -e "${RED}✗${NC} $message"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

# Header
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "1. CHECKING PREREQUISITES"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

# Check for required tools
echo "Checking required tools..."
TOOLS=("kubectl" "kustomize" "git")
for tool in "${TOOLS[@]}"; do
    if command_exists "$tool"; then
        print_status 0 "$tool is installed"
    else
        print_error "$tool is not installed"
    fi
done

echo ""

# Check git status
echo "Checking Git status..."
if [[ -d "$REPO_ROOT/.git" ]]; then
    print_status 0 "Git repository detected"

    # Check for uncommitted changes
    if git -C "$REPO_ROOT" diff-index --quiet HEAD --; then
        print_status 0 "No uncommitted changes"
    else
        print_warning "There are uncommitted changes in the repository"
    fi
else
    print_error "Not a Git repository"
fi

echo ""

# Header
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "2. VALIDATING COMPONENT STRUCTURE"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

# Check each component
total_yaml_files=0
for component in "${COMPONENTS[@]}"; do
    echo "Checking $component..."

    component_path="$REPO_ROOT/apps/$component"

    if [[ ! -d "$component_path" ]]; then
        print_error "$component directory not found at $component_path"
        continue
    fi

    print_status 0 "$component directory exists"

    # Check required files
    files_found=0
    for required_file in "${REQUIRED_FILES[@]}"; do
        if [[ -f "$component_path/$required_file" ]]; then
            ((files_found++))
        else
            print_error "Missing: $component/$required_file"
        fi
    done

    # Count total YAML files
    yaml_count=$(find "$component_path" -name "*.yaml" | wc -l)
    print_status 0 "Found $yaml_count YAML files in $component"
    ((total_yaml_files+=$yaml_count))

    echo ""
done

echo -e "Total YAML files: ${GREEN}$total_yaml_files${NC}\n"

# Header
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "3. VALIDATING KUSTOMIZE CONFIGURATIONS"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

# Validate kustomize for each component
for component in "${COMPONENTS[@]}"; do
    component_path="$REPO_ROOT/apps/$component/envs/prd"

    if [[ ! -d "$component_path" ]]; then
        print_error "Production environment not found: $component_path"
        continue
    fi

    echo "Validating $component/envs/prd..."

    if kustomize build "$component_path" >/dev/null 2>&1; then
        print_status 0 "Kustomize validation passed for $component"

        # Count manifests that would be generated
        manifest_count=$(kustomize build "$component_path" | grep -c "^apiVersion:" || true)
        echo "  ↳ Would generate ~$manifest_count Kubernetes objects"
    else
        print_error "Kustomize validation failed for $component"
        echo "  ↳ Run: kustomize build $component_path"
    fi

    echo ""
done

# Header
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "4. CHECKING INGRESS CONFIGURATION"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

ingress_components=("prometheus" "loki" "grafana")
for component in "${ingress_components[@]}"; do
    ingress_file="$REPO_ROOT/apps/$component/envs/prd/ingress.yaml"

    if [[ -f "$ingress_file" ]]; then
        print_status 0 "$component has ingress.yaml"

        # Check for Traefik IngressRoute
        if grep -q "traefik.io" "$ingress_file"; then
            echo "  ↳ Uses Traefik IngressRoute"
        fi

        # Extract domain
        domain=$(grep "Host(" "$ingress_file" | sed "s/.*Host(\`\([^']*\)\`).*/\1/" | head -1)
        if [[ -n "$domain" ]]; then
            echo "  ↳ Domain: $domain"
        fi
    else
        print_warning "$component is missing ingress.yaml"
    fi

    echo ""
done

# Header
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "5. CHECKING DOCUMENTATION"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

docs=(
    "PHASE_2_OBSERVABILITY_SETUP.md"
    "PHASE_2_COMPLETION_SUMMARY.md"
    "OBSERVABILITY_QUICK_START.md"
)

for doc in "${docs[@]}"; do
    doc_path="$REPO_ROOT/$doc"
    if [[ -f "$doc_path" ]]; then
        size=$(wc -c < "$doc_path")
        print_status 0 "$doc found ($(numfmt --to=iec $size 2>/dev/null || echo $size bytes))"
    else
        print_warning "$doc not found"
    fi
done

echo ""

# Header
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "6. CLUSTER READINESS CHECK"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

# Check if cluster is accessible
if kubectl cluster-info >/dev/null 2>&1; then
    print_status 0 "Kubernetes cluster is accessible"

    # Check for required storage class
    echo ""
    echo "Checking storage class..."
    if kubectl get storageclass longhorn-homelab >/dev/null 2>&1; then
        print_status 0 "Longhorn storage class 'longhorn-homelab' exists"

        # Check available space
        if command_exists "kubectl"; then
            longhorn_nodes=$(kubectl get nodes -l "node-role.kubernetes.io/master!=" | wc -l)
            echo "  ↳ Longhorn nodes: $((longhorn_nodes - 1))"
        fi
    else
        print_error "Longhorn storage class 'longhorn-homelab' not found"
        echo "  ↳ Ensure Longhorn is deployed before deploying observability stack"
    fi

    # Check for Traefik
    echo ""
    echo "Checking Ingress Controller..."
    if kubectl get deployment -A | grep -q traefik; then
        print_status 0 "Traefik ingress controller detected"
    else
        print_warning "Traefik ingress controller not found"
        echo "  ↳ Required for exposing Prometheus, Loki, and Grafana"
    fi

    # Check for cert-manager
    echo ""
    echo "Checking cert-manager..."
    if kubectl get namespace cert-manager >/dev/null 2>&1; then
        print_status 0 "cert-manager namespace found"

        # Check for letsencrypt-prod resolver
        if kubectl get clusterissuer letsencrypt-prod >/dev/null 2>&1 || \
           kubectl get issuer letsencrypt-prod -A >/dev/null 2>&1; then
            print_status 0 "Let's Encrypt production resolver configured"
        else
            print_warning "letsencrypt-prod issuer not found (TLS may fail)"
        fi
    else
        print_warning "cert-manager not detected"
        echo "  ↳ Required for automatic HTTPS certificates"
    fi

    # Check ArgoCD
    echo ""
    echo "Checking ArgoCD..."
    if kubectl get namespace argocd >/dev/null 2>&1; then
        print_status 0 "ArgoCD detected"

        # Check for applications
        app_count=$(kubectl -n argocd get applications --no-headers 2>/dev/null | wc -l || echo "0")
        echo "  ↳ Current applications: $app_count"
    else
        print_warning "ArgoCD not detected (manual deployment needed)"
    fi
else
    print_error "Cannot connect to Kubernetes cluster"
    echo "  ↳ Run: kubectl cluster-info"
fi

echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "VALIDATION SUMMARY"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo "Components validated: ${#COMPONENTS[@]}"
echo "Total YAML files: $total_yaml_files"
echo -e "Errors: ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"

echo ""

if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ All validations passed!                                ║${NC}"
    echo -e "${GREEN}║  Ready to deploy observability stack                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo "Next steps:"
    echo "1. Commit changes: git add apps/{prometheus,loki,promtail,grafana}"
    echo "2. Push to repository: git push origin main"
    echo "3. Watch deployment: kubectl -n argocd get applications -w"
    echo ""
    echo "Or manually deploy:"
    echo "  kustomize build apps/prometheus/envs/prd | kubectl apply -f -"
    echo "  kustomize build apps/loki/envs/prd | kubectl apply -f -"
    echo "  kustomize build apps/promtail/envs/prd | kubectl apply -f -"
    echo "  kustomize build apps/grafana/envs/prd | kubectl apply -f -"

    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ Validation failed with $ERRORS error(s)               ║${NC}"
    echo -e "${RED}║  Please fix issues before deploying                       ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"

    exit 1
fi
