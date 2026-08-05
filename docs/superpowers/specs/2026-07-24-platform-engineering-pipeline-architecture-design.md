# ADR: Three-Tier Reusable Pipeline Architecture

```
Status:      Proposed
Date:        2026-07-24
Decision-makers: Distinguished Engineer, CTO
Consulted:   DE DevEx, DE CI/CD, Adversarial Reviewer
Informed:    All engineers
Supersedes:  None
```

---

## Context

An engineering organization scaling from a handful of services toward thousands needs CI/CD pipelines that are **consistent, auditable, and zero-maintenance for service teams**. The traditional approach — copy-pasting workflow files into every repository — creates an O(N) maintenance burden that becomes untenable past ~20 services and catastrophic past ~100.

The platform team (today: 2 engineers) cannot be in the critical path of every service's CI/CD. Every pipeline change that requires touching N repositories is a multiplier on operational burden, a vector for configuration drift, and a compliance risk.

**Constraints:**

| Constraint | Implication |
|---|---|
| Platform team = 2 people | Zero-touch pipeline consumption for service teams |
| Scale target: 0 → 3,000+ services | O(1) pipeline changes, not O(N) |
| Multi-language (Go, Python, JavaScript) | Language-specific logic abstracted behind uniform interfaces |
| Compliance (SOC2, HIPAA, PHIPA) | Security scanning, SLSA provenance, secret detection baked in — not opt-in |
| GitOps-first (ArgoCD + Kargo) | Pipelines must produce OCI artifacts, compile Kustomize overlays, push config |
| Immutable versioning | No force-updated tags — consumers pin to semver, Renovate automates bumps |

---

## Problem

Without a structured pipeline architecture:

1. **Configuration drift**: 30 repos × 3 workflow files = 90 files to keep synchronized. One missed update means one service runs stale security scanning for months.
2. **Duplicated logic**: Container build steps, test sharding, coverage thresholds — reimplemented per repo with subtle inconsistencies.
3. **Compliance gaps**: Security scanning is opt-in. SLSA provenance is "someone should add that." Secret detection is "we'll get to it."
4. **Blast radius of changes**: Fixing a CVE in the build process requires PRs to every service repo. At 3,000 services, this is physically impossible without automation.
5. **Onboarding friction**: New services require assembling 500+ lines of workflow YAML. A senior engineer's first week is spent on plumbing instead of product.

---

## Decision

Adopt a **three-tier reusable pipeline architecture** organized into three repositories with a strict dependency hierarchy:

```
┌─────────────────────────────────────────────────────────┐
│                    SERVICE REPOS                        │
│           (consumers — 1-line workflow_call)             │
│                                                         │
│   service-a/             service-b/          service-n/ │
│     .github/workflows/     .github/workflows/           │
│       ci.yaml (3 lines)    ci.yaml (3 lines)            │
│       cd.yaml (3 lines)    cd.yaml (3 lines)            │
└────────────────────────┬────────────────────────────────┘
                         │ workflow_call (semver pin)
                         ▼
┌─────────────────────────────────────────────────────────┐
│              PLATFORM-ENGINEERING-WORKFLOWS              │
│          (pipeline orchestrators — the "what")           │
│                                                         │
│   ci-go.yaml          cd.yaml         release-go.yaml   │
│   ci-python.yaml      ci-gitops.yaml  release-python.yaml│
│   ci-javascript.yaml  sonarcloud.yaml release-js.yaml   │
│   cleanup-pr-image.yaml               cleanup-stale.yaml│
│                                                         │
│   12 orchestrators — one per lifecycle × language        │
└────────────────────────┬────────────────────────────────┘
                         │ workflow_call (semver pin)
                         ▼
┌─────────────────────────────────────────────────────────┐
│              PLATFORM-ENGINEERING-MODULES                │
│       (reusable workflow building blocks — the "how")    │
│                                                         │
│   50+ single-responsibility workflow modules:            │
│                                                         │
│   ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ │
│   │ Build        │ │ Test         │ │ Security       │ │
│   │ build-go     │ │ test-go      │ │ security       │ │
│   │ build-python │ │ test-python  │ │ trivy-scan     │ │
│   │ build-js     │ │ test-js      │ │ secret-detect  │ │
│   │ container    │ │ check-tests  │ │ slsa-provenance│ │
│   └──────────────┘ └──────────────┘ └────────────────┘ │
│   ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ │
│   │ Lint/Quality │ │ GitOps       │ │ Release        │ │
│   │ lint-go      │ │ oci-config   │ │ generate-rel   │ │
│   │ lint-python  │ │ argocd-diff  │ │ release-notes  │ │
│   │ lint-js      │ │ compile-pr   │ │ release-please │ │
│   │ pre-commit-* │ │ kustomize    │ │ verify-release │ │
│   │ sonarcloud   │ │ kubeconform  │ │ release-arts   │ │
│   └──────────────┘ └──────────────┘ └────────────────┘ │
│   ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ │
│   │ Validation   │ │ Reporting    │ │ Environment    │ │
│   │ branch-name  │ │ pr-status    │ │ detect-env     │ │
│   │ semver       │ │ cd-summary   │ │ get-deploy-info│ │
│   │ conv-commits │ │ notify-fail  │ │ golden-image   │ │
│   │ yaml-lint    │ │ job-summary  │ │ github-vars    │ │
│   │ pipeline-val │ │              │ │                │ │
│   └──────────────┘ └──────────────┘ └────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ uses: (composite action)
                         ▼
┌─────────────────────────────────────────────────────────┐
│             PLATFORM-ENGINEERING-ACTIONS                 │
│       (atomic composite actions — the "mechanics")       │
│                                                         │
│   24+ composite GitHub Actions:                          │
│                                                         │
│   parse-config          check-tests     setup-cli        │
│   parse-deployment      pr-feedback     setup-sonar      │
│   configure-private-deps check-coverage setup-kubeconform│
│   detect-test-failures  install-node    setup-kyverno    │
│   extract-test-metrics  argocd-auth     resolve-sonar    │
│   aggregate-results     capture-debug   track-performance│
│   restore-cached-tests  write-summary   openspec         │
│   artifacts-and-summary                                  │
└─────────────────────────────────────────────────────────┘
```

**Dependency chain (strict, unidirectional):**

```
platform-engineering-actions
        ↑ consumed by
platform-engineering-modules
        ↑ consumed by
platform-engineering-workflows
        ↑ consumed by
service repos (ALL consumers)
```

---

## Rationale: Why Three Tiers

### 1. Separation of Concerns by Blast Radius

Each tier has a different **change frequency**, **blast radius**, and **audience**:

| Tier | Change Frequency | Blast Radius | Audience |
|---|---|---|---|
| **Actions** (mechanics) | Rare — shell logic, parsing | Contained: only modules that use it | Platform engineers |
| **Modules** (building blocks) | Moderate — new scanners, test strategies | Medium: orchestrators that compose it | Platform engineers |
| **Workflows** (orchestrators) | Frequent — new languages, policy changes | Wide: all consumer services | Platform + service teams |

A bug in `check-tests` (action) affects only the `test-*.yaml` modules that use it — not the CD pipeline, not the release pipeline. A 2-tier system (actions + pipelines) would conflate building blocks with orchestration, meaning every module-level change touches the consumer-facing contract.

### 2. O(1) Changes at Scale

**The architecture's defining property: changing pipeline behavior for all services requires modifying exactly 1 file, in exactly 1 repository.**

| Scenario | Three-tier (this architecture) | Copy-paste (status quo alternative) |
|---|---|---|
| Add SLSA provenance to all builds | Edit `container.yaml` in modules, bump 1 version | Edit N service repos, miss 12, audit 3 months later |
| Fix CVE in build tooling | Patch action, cascade bump | PRs to every repo, 2-week tail of stragglers |
| Add new language (Rust) | Add `ci-rust.yaml` orchestrator + `build-rust.yaml` module | Template from scratch, no consistency guarantee |
| Enforce coverage threshold | Change default in `ci-*.yaml` input | Hope every repo copied the right default |

At 3,000 services, O(N) changes are not "expensive" — they are **impossible** for a 2-person platform team. O(1) changes are existential.

### 3. Consumer Simplicity (3-Line Adoption)

A service team's entire CI pipeline is a minimal workflow file:

```yaml
# .github/workflows/ci.yaml
name: CI
on: [pull_request]
jobs:
  ci:
    uses: org/platform-engineering-workflows/.github/workflows/ci-go.yaml@v1.6.0
    secrets: inherit
```

Per-service configuration lives in the **service DSL** — a declarative manifest already present in every service repo. The `parse-config` action extracts language, domain, testing flags, deployment topology, and all other service-specific parameters from this manifest. The pipeline adapts its behavior accordingly:

```
service DSL → parse-config action → pipeline inputs
                                     ├── language: go | python | javascript
                                     ├── testing.integration.enabled: true/false
                                     ├── testing.e2e.enabled: true/false
                                     ├── artifact-type: docker | oci
                                     └── deployment topology (environments, regions)
```

**The consumer workflow file never changes.** All customization flows through the service DSL, which service teams already own and maintain for deployment configuration. The pipeline reads it — service teams don't need to learn a separate pipeline config format.

**DevEx impact:**
- New service onboarding: **< 5 minutes** (copy workflow file, write service DSL, push)
- Zero pipeline internals to understand or maintain
- Compliance is automatic, not opt-in
- Updates arrive via Renovate PR — approve and merge
- Per-service customization flows through the existing service DSL — no new config format to learn

### 4. Immutable Versioning with Cascade Bumps

Every tier uses **semver tags**, never mutable branch refs:

```
platform-engineering-actions    → v1.3.0
platform-engineering-modules    → v1.9.11  (pins actions@v1.3.0)
platform-engineering-workflows  → v1.6.2   (pins modules@v1.9.11)
service repos                   → pin workflows@v1.6.2
```

**Why immutable tags matter:**
- GitHub Actions caches tag → SHA resolution. Force-updating a tag means consumers silently run stale code.
- Renovate can only track semver tags — `@main` refs are invisible to dependency management.
- Audit trail: every service's CI behavior is deterministic from its pinned version. Compliance auditors can verify exactly what ran.

**Cascade protocol:** When an action changes, the bump propagates upward:
1. Tag actions → bump modules refs → tag modules → bump workflow refs → tag workflows → bump all consumers → verify zero stragglers.
2. The cascade completes in one session. Partial bumps create version drift that breaks CI unpredictably.

### 5. Secret Propagation via `secrets: inherit`

Consumer repos pass secrets to orchestrators using `secrets: inherit`, which forwards all repository secrets through the workflow chain. This is a deliberate trade-off:

```yaml
# Consumer workflow — minimal surface
jobs:
  ci:
    uses: org/platform-engineering-workflows/.github/workflows/ci-go.yaml@v1.6.0
    secrets: inherit
```

**Why `inherit` over scoped secrets:**
- **Consumer simplicity** — service teams never need to know which secrets the pipeline requires. Adding a new security scanner that needs a new token is an orchestrator change, not a consumer change.
- **Zero consumer-side maintenance** — no consumer workflow edits when the platform adds or removes a secret dependency.
- **Practical security boundary** — the pipeline repos are platform-team owned and code-reviewed. The trust boundary is the repo, not individual workflow steps. Composite actions in the actions tier are internal code, not third-party.

**Accepted risk:** A compromised action within the platform repos would have access to all consumer secrets. This is mitigated by:
- Platform repos require PR review by platform engineers before merge
- All composite actions are first-party code (no third-party actions in the chain)
- GitHub's OIDC token scoping limits what secrets can do outside the workflow run
- The platform repos' dependency chain is pinned to SHA — no transitive supply-chain risk from mutable refs

### 6. Security by Default, Not by Configuration

Every CI pipeline automatically includes — with no opt-in required:

| Security Control | Implementation | Tier |
|---|---|---|
| **Secret detection** | TruffleHog/Gitleaks in pre-commit | Module: `secret-detection-gitops.yaml` |
| **Container scanning** | Trivy with severity thresholds | Module: `trivy-docker-scan.yaml` |
| **SAST** | SonarCloud with quality gates | Module: `sonarcloud.yaml` |
| **SLSA provenance** | Cosign keyless signing + attestation | Module: `slsa-provenance.yaml` |
| **Dependency audit** | Language-native (govulncheck, pip-audit, npm audit) | Module: `security.yaml` |
| **Golden image validation** | Base image allowlist enforcement | Module: `validate-golden-image.yaml` |
| **Branch protection** | Conventional commits + branch name validation | Module: `validate-branch-name.yaml` |
| **Policy enforcement** | Kyverno dry-run against cluster policies | Module: `kyverno-dry-run.yaml` |
| **Kubernetes validation** | Kubeconform schema validation | Module: `kubeconform.yaml` |

A service team cannot accidentally skip security scanning. It is impossible to opt out without forking the pipeline — which is a visible, auditable decision.

### 7. Language Abstraction with Uniform Interface

All language-specific pipelines expose the same `workflow_call` inputs:

```yaml
inputs:
  coverage-threshold:   { type: number,  default: 80 }
  build-container:      { type: boolean, default: true }
  enable-integration:   { type: boolean, default: false }
  enable-e2e:           { type: boolean, default: false }
  upload-sarif:         { type: boolean, default: false }
  artifact-type:        { type: string,  default: "docker" }
```

Whether the service is Go, Python, or JavaScript, the consumer interface is identical. Language-specific logic (test runners, linters, build tools) is encapsulated in the modules tier. Adding a new language means:
1. Create `build-<lang>.yaml`, `test-<lang>.yaml`, `lint-<lang>.yaml` modules
2. Create `ci-<lang>.yaml` orchestrator that composes them
3. Tag and bump — existing services are unaffected

### 8. GitOps-Native CD Pipeline

The CD pipeline is not a deployment tool — it is a **GitOps artifact producer**:

```
CD Pipeline Flow:
  detect-environment → validate-golden-image → build-container → scan-container
  → sign-container (Cosign) → push-to-registry (GHCR)
  → compile-gitops-config → push-oci-artifact → trigger-argocd-sync
  → generate-release → release-notes → cd-summary
```

The pipeline never `kubectl apply`s. It produces signed, scanned OCI artifacts and pushes GitOps configuration. ArgoCD reconciles the desired state. This separation means:
- **Rollback** = revert a git commit (not "re-run the pipeline backwards")
- **Audit** = git history shows exactly what changed and who approved it
- **Multi-environment** = same artifact, different config overlays (dev → staging → production via Kargo promotion)

---

## Alternatives Considered

### Alternative 1: Monolithic Pipeline (Single Repo)

Combine all actions, modules, and orchestrators into one repository.

| Aspect | Assessment |
|---|---|
| Simplicity | Fewer repos to manage |
| Versioning | Single version for everything — a lint fix bumps the same version as a CD overhaul |
| Blast radius | Any change affects all consumers simultaneously |
| Team autonomy | Impossible to scope access — module contributor can break orchestrators |
| **Verdict** | **Rejected.** Coarse versioning creates coupling. A lint module patch forces all consumers to bump, creating unnecessary churn and risk. |

### Alternative 2: Two-Tier (Actions + Pipelines Only)

Skip the modules tier — orchestrators directly embed reusable logic.

| Aspect | Assessment |
|---|---|
| Simplicity | Fewer repos |
| Reuse | Orchestrators duplicate shared logic (container builds, test patterns) |
| File size | Orchestrators grow to 1,000+ lines — unmaintainable |
| Composition | Cannot mix-and-match building blocks for new pipeline patterns |
| **Verdict** | **Rejected.** The modules tier is the composition layer that prevents orchestrator bloat. Without it, `ci-go.yaml` and `ci-python.yaml` duplicate 60% of their logic. |

### Alternative 3: Copy-Paste with Template Generation

Generate per-repo workflow files from a central template (Cookiecutter, Copier, etc.).

| Aspect | Assessment |
|---|---|
| Initial simplicity | Easy to understand — "it's just files" |
| Drift | Generated files diverge immediately upon manual edits |
| Updates | Re-running the generator clobbers local customizations |
| Scale | At 3,000 repos, regeneration is a multi-hour batch job with merge conflicts |
| Compliance | No guarantee that security scanning is present — only that it was present at generation time |
| **Verdict** | **Rejected.** Generation creates the illusion of consistency. The moment a service team edits a generated file, drift begins. Reusable workflows enforce consistency at runtime, not at generation time. |

### Alternative 4: Centralized CI/CD Platform (Jenkins, Tekton, Dagger)

Replace GitHub Actions with a dedicated CI/CD platform.

| Aspect | Assessment |
|---|---|
| Power | Full programmability, complex DAGs |
| Ops burden | Self-hosted infrastructure to maintain (Jenkins controllers, Tekton pipelines) |
| Team knowledge | Engineers must learn a new system instead of using GitHub-native tooling |
| Integration | GitHub PR checks, branch protection, CODEOWNERS — all require custom integration |
| Cost | Infrastructure + ops hours >> GitHub Actions usage |
| **Verdict** | **Rejected.** For a 2-person platform team, self-hosted CI/CD is an operational trap. GitHub Actions reusable workflows provide 90% of the capability at 10% of the operational burden. |

---

## Consequences

### Positive

- **O(1) pipeline governance**: Policy changes (coverage thresholds, scanner versions, signing requirements) propagate to all services via one version bump
- **3-line consumer adoption**: Service teams write zero pipeline YAML beyond the `workflow_call` invocation
- **Security by default**: Container scanning, SLSA provenance, secret detection, SAST — all mandatory, zero configuration
- **Compliance audit trail**: Every pipeline version is immutable and deterministic — auditors can verify exactly what ran on any commit
- **Language-agnostic growth**: Adding Rust, Java, or any new language is additive — existing pipelines are untouched
- **Renovate-automated updates**: Service teams receive version bump PRs automatically — review, approve, merge
- **2-person scalability**: The platform team maintains 3 repos, not N repos. The architecture scales to 3,000 services without additional pipeline engineers

### Negative

- **Cascade bump ceremony**: A change in actions requires tagging 3 repos and bumping all consumers within the cascade SLA. This is deliberate friction that prevents partial updates. At scale, automation (Renovate batch PRs + auto-merge) handles propagation.
- **Debugging indirection**: A failing CI step requires tracing through orchestrator → module → action. Mitigated by structured error blocks in job summaries, read access to all platform repos, and resolved-version reporting in every pipeline run.
- **GitHub Actions nesting at hard limit**: The 4-level nesting is at GitHub's maximum. Contingency plan documented: composite actions (non-workflow) can reclaim one level if GitHub reduces the limit.
- **Vendor coupling to GitHub Actions**: The architecture is GitHub-native. Migration requires rewriting orchestration YAML but not business logic (portable shell scripts in composite actions). The three-tier design principles are runtime-agnostic. This is a documented one-way door.
- **`secrets: inherit` trust boundary**: All consumer secrets are available to the full pipeline chain. Mitigated by first-party-only actions, PR review requirements, and SHA-pinned dependencies. The trust boundary is the platform repo, not individual steps.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GitHub Actions nesting limit reduced | Low | High | Contingency plan: convert thin modules to composite actions (reclaims 1 level) |
| Cascade bump missed (partial drift) | Medium | Medium | Automated verification script + zero-straggler check; cascade failure runbook |
| Module becomes too large | Medium | Low | Split into sub-modules; modules tier is designed for composition |
| Renovate PR fatigue for consumers | Medium | Low | Batch dependency updates; auto-merge for patch versions with passing CI |
| Bad module tag propagated before detection | Low | High | Canary consumer validates before fleet cascade; rollback = new patch tag + resume cascade |
| GitHub Actions outage | Low | High | Single vendor dependency; business logic is portable shell scripts. No fallback CI during outage — accept and document |
| GHA minutes cost at scale | Medium | Medium | Pipeline SLOs enforce execution time budgets; consolidate sub-15s jobs to reduce 1-min billing floor waste |

---

## Implementation: Repository Structure

### platform-engineering-actions (Tier 1 — Mechanics)

```
platform-engineering-actions/
├── check-tests/
│   └── action.yaml          # Detect test types, calculate shards
├── parse-config/
│   └── action.yaml          # Parse service DSL configuration
├── parse-deployment-config/
│   └── action.yaml          # Extract deployment topology
├── configure-private-deps/
│   └── action.yaml          # Authenticate to private registries
├── detect-test-failures/
│   └── action.yaml          # Parse test output for failures
├── extract-test-metrics/
│   └── action.yaml          # Coverage, duration, flakiness
├── aggregate-test-results/
│   └── action.yaml          # Merge results from sharded runs
├── pr-feedback/
│   └── action.yaml          # Post PR comments with results
├── setup-cli/
│   └── action.yaml          # Install platform CLI
├── setup-sonarcloud-project/
│   └── action.yaml          # Bootstrap SonarCloud integration
├── setup-kubeconform/
│   └── action.yaml          # Install kubeconform
├── setup-kyverno-cli/
│   └── action.yaml          # Install kyverno CLI
├── track-performance/
│   └── action.yaml          # Record pipeline performance metrics
├── write-job-summary/
│   └── action.yaml          # Generate GitHub job summary
└── renovate.json             # Self-managed dependency updates
```

### platform-engineering-modules (Tier 2 — Building Blocks)

```
platform-engineering-modules/
└── .github/workflows/
    ├── build-go.yaml              # Go binary compilation
    ├── build-python.yaml          # Python wheel/sdist build
    ├── build-js.yaml              # Node.js build + bundle
    ├── test-go.yaml               # Go test execution (sharded)
    ├── test-python.yaml           # pytest execution (sharded)
    ├── test-js.yaml               # Jest/Vitest execution (sharded)
    ├── lint-go.yaml               # golangci-lint
    ├── lint-python.yaml           # ruff + mypy
    ├── lint-js.yaml               # eslint + prettier
    ├── container.yaml             # Unified container build (Docker/Buildx)
    ├── security.yaml              # Language-native vulnerability scanning
    ├── sonarcloud.yaml            # SAST + quality gates
    ├── trivy-docker-scan.yaml     # Container image scanning
    ├── slsa-provenance.yaml       # Cosign signing + SLSA attestation
    ├── secret-detection-gitops.yaml # GitOps secret scanning
    ├── validate-golden-image.yaml # Base image allowlist enforcement
    ├── validate-branch-name.yaml  # Branch naming convention
    ├── validate-semver.yaml       # Semantic version validation
    ├── conventional-commits.yaml  # Commit message enforcement
    ├── pre-commit-go.yaml         # Go-specific pre-commit hooks
    ├── pre-commit-python.yaml     # Python-specific pre-commit hooks
    ├── pre-commit-js.yaml         # JS-specific pre-commit hooks
    ├── compile-pr-values.yaml     # Compile PR environment config
    ├── oci-config-push.yaml       # Push GitOps config as OCI artifact
    ├── argocd-diff.yaml           # ArgoCD app-of-apps diff preview
    ├── kustomize-build.yaml       # Kustomize overlay validation
    ├── kubeconform.yaml           # Kubernetes manifest validation
    ├── kyverno-dry-run.yaml       # Policy dry-run validation
    ├── detect-environment.yaml    # Environment detection logic
    ├── get-deployment-info.yaml   # Deployment topology extraction
    ├── generate-release.yaml      # Release creation
    ├── release-notes.yaml         # Changelog generation
    ├── release-please.yaml        # Automated release management
    ├── release-artifacts.yaml     # Binary/asset publishing
    ├── verify-release.yaml        # Post-release verification
    ├── pr-status.yaml             # PR check summary
    ├── cd-summary.yaml            # CD pipeline summary
    ├── notify-failure.yaml        # Failure notification
    ├── cache-seed-pre-commit.yaml # Pre-commit cache warming
    ├── check-tests.yaml           # Test discovery orchestration
    ├── parse-test-config.yaml     # Test configuration parsing
    ├── pipeline-phase-validation.yaml # Phase gate enforcement
    ├── create-security-issue.yaml # Auto-create security issues
    ├── update-github-variables.yaml # Environment variable sync
    └── yaml-lint.yaml             # YAML linting
```

### platform-engineering-workflows (Tier 3 — Orchestrators)

```
platform-engineering-workflows/
└── .github/workflows/
    ├── ci-go.yaml                 # Go CI orchestrator
    ├── ci-python.yaml             # Python CI orchestrator
    ├── ci-javascript.yaml         # JavaScript CI orchestrator
    ├── ci-gitops.yaml             # GitOps repo CI orchestrator
    ├── cd.yaml                    # Continuous Deployment orchestrator
    ├── release-go.yaml            # Go release orchestrator
    ├── release-python.yaml        # Python release orchestrator
    ├── release-js.yaml            # JavaScript release orchestrator
    ├── sonarcloud-baseline.yaml   # SonarCloud baseline scan
    ├── cleanup-pr-image.yaml      # PR environment cleanup
    └── cleanup-stale-pr-branches.yaml # Stale branch cleanup
```

---

## Versioning Protocol

### Ref Format (Renovate-Compatible)

Consumer repos pin using SHA + semver comment for maximum security and automation:

```yaml
# Format: SHA pin + tag comment (Renovate-managed)
uses: org/platform-engineering-modules/.github/workflows/container.yaml@3c9fbfa03978275be91d4a424f6808d721410c74 # v1.9.11
```

- SHA provides immutable, tamper-proof resolution
- Semver comment enables Renovate tracking and human readability
- Both SHA and comment are updated together — never one without the other

### Cascade Bump Protocol

```
Action changed:
  1. Tag actions (v1.3.1)
  2. Bump action refs in modules → tag modules (v1.9.12)
  3. Bump module refs in workflows → tag workflows (v1.6.3)
  4. Bump workflow refs in ALL consumer repos
  5. Verify zero stragglers

Module changed:
  1. Tag modules (v1.9.12)
  2. Bump module refs in workflows → tag workflows (v1.6.3)
  3. Bump workflow refs in ALL consumer repos
  4. Verify zero stragglers

Workflow changed:
  1. Tag workflows (v1.6.3)
  2. Bump workflow refs in ALL consumer repos
  3. Verify zero stragglers
```

**Invariant: the cascade converges monotonically within the defined SLA. Partial bumps are forbidden.**

### Cascade SLA by Scale Tier

The "O(1) authoring" claim is precise — modifying pipeline behavior requires changing exactly 1 file. However, **propagation** to consumers is O(N) via Renovate PRs. This is a deliberate trade-off: the propagation is automated, asynchronous, and does not require platform team involvement at scale.

| Scale | Services | Cascade SLA | Mechanism |
|---|---|---|---|
| **Startup** (1–10) | 10 | < 30 minutes | Manual bump, verify in one session |
| **Growth** (10–100) | 100 | < 2 hours | Renovate PRs, manual merge |
| **Scale** (100–1,000) | 1,000 | < 24 hours | Renovate batch PRs, auto-merge for passing patches |
| **Enterprise** (1,000–3,000+) | 3,000 | < 48 hours | Tiered rollout: canary (10) → batch (100) → fleet |

**Tiered rollout at enterprise scale:**
1. **Canary consumer** (dedicated test-consumer repo with comprehensive integration tests) — bumped and validated first
2. **Early adopters** (10 services with high test coverage) — batch Renovate PR
3. **Fleet** (remaining services) — batch Renovate PR with auto-merge for patch versions when CI passes

**Rate limit mitigation:** Renovate's built-in rate limiting and concurrent PR limits prevent GitHub API throttling. PRs are opened in batches, not simultaneously.

### Cascade Failure Runbook

When a cascade fails partway (bad module tag, flaky canary, API rate limit):

1. **Identify the bad version:** Which tag introduced the failure?
2. **Do NOT revert the tag** — GitHub caches tag → SHA. A force-updated tag creates ghost state.
3. **Tag a new patch version** that reverts the change (e.g., v1.9.13 reverts v1.9.12)
4. **Resume the cascade** with the fix version — bump all consumers to v1.9.13
5. **Verify zero stragglers** — no consumer should remain on the broken v1.9.12

**The cascade is append-only.** Fix forward, never rewrite history.

---

## Pipeline Testing Strategy

Pipeline infrastructure is production code. A bad module tag at 500+ consumers is an incident.

### Pre-Tag Validation

Every module and action change is validated **before tagging**:

1. **Synthetic consumer tests**: A dedicated `platform-pipeline-tests` repository contains one workflow per orchestrator type. Each workflow exercises the full CI/CD pipeline path against a minimal test service. PRs to module/action repos trigger these synthetic consumers via `workflow_dispatch`.

2. **Canary consumer**: A real service repo (`canary-service`) is always bumped first during cascade. It runs a comprehensive test suite that exercises edge cases (monorepo paths, custom coverage thresholds, integration tests, container builds). The cascade does not proceed until the canary passes.

3. **Schema validation**: A linter validates that all `workflow_call` inputs and outputs in modules match the contracts expected by orchestrators. Breaking changes are caught before they reach consumers.

### Post-Tag Monitoring

After a cascade completes:
- `track-performance` action reports execution time, step duration, and failure rates to a fleet-wide dashboard
- Anomaly detection alerts if P95 CI time exceeds the defined SLO after a version bump
- `verify-release` module validates that the tagged version produces the expected artifacts

---

## Pipeline Performance SLOs

Pipeline performance is a product metric, not an afterthought:

| Metric | Target | Measurement |
|---|---|---|
| CI P50 execution time | < 6 minutes | `track-performance` action |
| CI P95 execution time | < 12 minutes | `track-performance` action |
| CD P50 execution time | < 8 minutes | `track-performance` action |
| CD P95 execution time | < 15 minutes | `track-performance` action |
| Pipeline reliability | > 99.5% (excl. legitimate test failures) | Failure rate tracking |
| Cascade propagation | Within SLA per scale tier | Straggler verification |

**Enforcement:** The `track-performance` action records timing data. A weekly report surfaces pipelines that exceed SLOs. Modules that contribute disproportionate execution time are candidates for optimization or parallelization.

**Cost awareness:** At enterprise scale (3,000 services × ~15 GHA minutes/CI run × ~20 PRs/week/service), GitHub Actions consumption is a material budget line. The performance SLOs serve a dual purpose: developer experience and cost control. Modules that waste billable minutes (e.g., jobs that run <15s but bill at GHA's 1-minute floor) are consolidated.

---

## Developer Experience: Debugging and Observability

The three-tier indirection creates a debugging challenge: a failing CI step requires tracing through orchestrator → module → action. This is the architecture's primary DevEx cost, and it is mitigated deliberately.

### Platform Repository Access

**All platform repos (workflows, modules, actions) are read-accessible to every engineer.** Debugging opaque pipelines without source access is unacceptable. Engineers can read the module source to understand what a failing step does, even though they cannot modify it.

### Structured Error Reporting

Every module emits a structured error block in the GitHub Actions job summary:

```
┌─────────────────────────────────────────────┐
│ ❌ Pipeline Failure — test-go.yaml          │
│                                             │
│ Module:    platform-engineering-modules@v1.9.11 │
│ Action:    detect-test-failures@v1.3.0      │
│ Phase:     Unit Tests (shard 2/4)           │
│ Error:     TestUserService_Create FAIL      │
│                                             │
│ Source:    org/platform-engineering-modules  │
│            .github/workflows/test-go.yaml   │
│                                             │
│ Resolved versions:                          │
│   workflows: v1.6.2                         │
│   modules:   v1.9.11                        │
│   actions:   v1.3.0                         │
└─────────────────────────────────────────────┘
```

This tells the developer: what failed, where in the pipeline, which versions were involved, and a direct path to the source.

### Extension Points

Orchestrators provide pre/post hook extension points for services that need custom pipeline steps:

```yaml
inputs:
  pre-test-script:
    type: string
    default: ""
    description: Script to run before test phase (e.g., database migration dry-run)
  post-build-script:
    type: string
    default: ""
    description: Script to run after build phase (e.g., custom artifact processing)
```

This prevents the primary escape hatch failure mode: teams forking the orchestrator to add one custom step, creating drift that undermines the entire architecture.

### Module Classification

Each module is classified as **policy-mandatory** or **optional**:

| Classification | Modules | Can be skipped? |
|---|---|---|
| **Policy-mandatory** | secret-detection, trivy-scan, slsa-provenance, golden-image-validation, conventional-commits | No — compliance requirement |
| **Optional** | sonarcloud, e2e tests, integration tests, argocd-diff | Yes — via workflow input toggle |

This distinction is critical: service teams know which modules they can tune and which are non-negotiable organizational policy.

---

## One-Way Doors

Two decisions in this architecture are effectively irreversible past certain adoption thresholds. Per the CTO decision rubric, one-way doors require explicit acknowledgment:

### Door 1: Three-Tier Structure

**Reversibility window:** < 50 consumers
**Past threshold:** Collapsing tiers (3 → 2 or 3 → 1) requires migrating all consumers' workflow refs, which at 200+ services is a multi-month project.
**Mitigation:** The tier boundaries are the stable contract. Internal module composition can change freely without consumer impact.

### Door 2: GitHub Actions as Runtime

**Reversibility window:** Always reversible in theory, 2+ months in practice at scale
**Past threshold:** Business logic lives in portable shell scripts inside composite actions. The GitHub Actions YAML is orchestration glue. A migration to Dagger/Tekton would rewrite the orchestration layer but preserve the business logic.
**Mitigation:** The three-tier design principles (separation by blast radius, O(1) authoring, scoped secrets, immutable versioning) are runtime-agnostic. Only the YAML syntax is GitHub-specific.

---

## Nesting Limit Contingency

The architecture uses exactly 4 nesting levels — GitHub Actions' hard maximum. This is zero headroom.

**Contingency plan if GitHub reduces the limit to 3:**

| Option | Description | Impact |
|---|---|---|
| **Inline actions into modules** | Composite actions become `run:` steps inside module workflows | Eliminates Tier 1 as separate repo; acceptable because actions change rarely and their shell logic is portable |
| **Convert actions to composite actions** | Composite actions (non-workflow) do not count toward the nesting limit | Reclaims one nesting level; requires refactoring actions from `workflow_call` to `uses: ./action` |
| **Flatten orchestrators** | Merge module calls into orchestrator YAML | Destroys the composition layer; last resort |

**Preferred contingency:** Option 2 (composite actions). This is already partially implemented — 24 actions in Tier 1 are composite actions. Expanding this pattern to modules that are thin wrappers would reclaim headroom without sacrificing the architecture's core separation.

---

## Contribution Model

The pipeline repos are owned by the platform team but accept contributions from all engineers:

| Role | Access | Can do |
|---|---|---|
| Platform engineers | Write | Merge to main, create tags, execute cascades |
| Service engineers | Read + PR | Submit PRs to modules/actions, propose new modules |
| Tech leads | Read + Approve | Review and approve pipeline PRs that affect their team |

**Contribution guidelines:**
1. Every PR must include a synthetic consumer test that exercises the change
2. Breaking changes (removed inputs, changed defaults) require an RFC comment on the PR with migration path
3. New modules must include a structured error block in the job summary
4. All PRs are reviewed by at least one platform engineer before merge

This addresses the bus-factor risk: if a platform engineer is unavailable, service engineers can submit fixes and tech leads can approve them. The cascade execution remains a platform-team responsibility.

---

## Scale Trajectory

| Scale | Services | Pipeline Repos | Consumer Effort | Platform Effort |
|---|---|---|---|---|
| **Startup** | 1–10 | 3 repos, ~30 modules | 3-line workflow file | Build initial modules |
| **Growth** | 10–100 | Same 3 repos, ~50 modules | Same 3-line file | Add modules as needed |
| **Scale** | 100–1,000 | Same 3 repos, ~80 modules | Same 3-line file | Renovate handles bumps |
| **Enterprise** | 1,000–3,000+ | Same 3 repos, ~120 modules | Same 3-line file | Policy-as-code, auto-merge |

The consumer interface never changes. The platform team adds modules and orchestrators. Renovate automates version propagation. At enterprise scale, patch-version bumps auto-merge when CI passes — the platform team is out of the hot path entirely.

---

## Decision Review Criteria

- **Revisit if:** GitHub Actions removes reusable workflow support or reduces nesting limit below 4
- **Revisit if:** Platform team exceeds 10 engineers (may warrant a dedicated CI/CD platform with the ops capacity to run it)
- **Revisit if:** Cascade propagation consistently exceeds defined SLA at current scale tier
- **Revisit if:** GHA minutes cost exceeds 2x the cost of a self-hosted CI/CD platform
- **Revert if:** Cascade bump ceremony exceeds 4 hours per change at < 100 services (indicates the architecture has outgrown GitHub Actions prematurely)
- **Supersede when:** The organization adopts a dedicated CI/CD platform (Dagger, Tekton) — the three-tier design principles still apply, only the runtime changes

---

## Appendix: Agent Review Verdicts

This ADR was reviewed by three advisory agents before finalization. Their findings are incorporated throughout the document.

| Agent | Verdict | Key Findings Incorporated |
|---|---|---|
| **CTO Advisor** | 🟡 Approve with notes | Cascade automation at scale, one-way doors labeled, pipeline SLOs, cost awareness, access control model |
| **DE DevEx** | 🟡 Approve with notes | Service DSL as config source (existing, not new `.platform.yaml`), structured error blocks, read access mandate, pre/post hooks, module classification, Renovate batching |
| **Adversarial Reviewer** | 🟡 Ship with mitigations | [SEV-1] Secret trust boundary documented, [SEV-1] Cascade SLA by scale tier, [SEV-2] Nesting contingency plan, [SEV-2] Pipeline testing strategy, [SEV-3] Contribution model |

All three agents' findings were addressed. No SEV-1 findings remain open.
