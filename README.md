<div align="center">

# DevSecOps Pipeline

**Every commit: tested, signed, shipped.**

A secure CI/CD pipeline, end to end: multi-arch images, supply-chain security,
Kubernetes E2E tests on every pull request and GitOps delivery.

[![CI/CD](https://github.com/EA-etn/devsecops-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/EA-etn/devsecops-pipeline/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/EA-etn/devsecops-pipeline?color=8b5cf6)](https://github.com/EA-etn/devsecops-pipeline/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-10b981)](LICENSE)
![Kubernetes](https://img.shields.io/badge/Kubernetes-k3s-326CE5?logo=kubernetes&logoColor=white)
![Signed with Cosign](https://img.shields.io/badge/signed-Cosign-f97316?logo=sigstore&logoColor=white)

**English** · [Español](README.es.md)

<img src="docs/diagrams/en/01-general.svg" alt="Architecture overview: code, CI/CD, supply chain and runtime layers" width="100%">

<sub><a href="https://raw.githubusercontent.com/EA-etn/devsecops-pipeline/main/docs/diagrams/en/01-general.png">🔍 View full size</a></sub>

</div>

## Why this project

The project is the **pipeline**. The app it delivers, **`demo-api`**, is intentionally tiny (a few
JSON endpoints in FastAPI): it is the passenger. The point is everything around it, the same
practices a platform team uses to ship software safely.

- **Nothing broken reaches `main`:** every pull request runs tests, security scans and a real
  deployment on a 3-node Kubernetes cluster.
- **Every image is verifiable:** scanned with Trivy, shipped with an SBOM and provenance, and
  signed with Cosign, with no keys to manage.
- **Git is the source of truth:** the pipeline writes the exact version to deploy, and ArgoCD
  syncs the cluster from Git.

## In numbers

| | |
|---|---|
| ⏱️ **~3 min** | From opening a pull request to a verdict, including a real deployment on a 3-node Kubernetes cluster |
| 🚀 **~2 min** | From merge to a scanned, signed image in the registry and the GitOps commit |
| ✅ **0** | Failed requests tolerated during a rolling update. CI sends continuous traffic and fails on the first error |
| 🛡️ **2** | Vulnerable images stopped by the security gate on `main` before they were signed or deployed |
| 🔁 **19** | Deployments to the homelab so far. Every one is a Git commit made by the pipeline, none a manual `kubectl` |
| 📓 **13** | Real incidents [written up](docs/lessons-learned.md) with root cause and fix |

<sub>Times are the median of the last 20 pipeline runs (November 2026).</sub>

## Highlights

| Area | What you get |
|---|---|
| 🐳 **Container** | Multi-stage build · non-root user · healthcheck · `amd64` + `arm64` (runs on a Raspberry Pi) |
| 🔐 **DevSecOps** | Trivy (deps, secrets, misconfig, image) · SBOM · SLSA provenance · Cosign keyless · Dependabot · SHA-pinned actions |
| ☸️ **Kubernetes** | Helm chart with *restricted* Pod Security, probes, PDB, HPA, topology spread and `helm test` |
| 🧪 **CI** | E2E on an ephemeral **3-node k3s cluster** in every PR, including a zero-downtime rolling update |
| 🔄 **GitOps** | Automatic image-tag commit after each merge + ArgoCD `Application` (auto-sync, self-heal, prune) |
| 📊 **Observability** | `/metrics` in Prometheus format + `ServiceMonitor`. In the [homelab](https://github.com/EA-etn/homelab-k3s): Grafana dashboards, SLOs, burn-rate alerts to Telegram |

## Quick start

```bash
docker run -p 8000:8000 ghcr.io/ea-etn/demo-api:0.4.0
curl localhost:8000/info
```

Or from source:

```bash
make install   # virtualenv + dependencies
make test      # tests
make run       # http://localhost:8000/docs
make help      # every command
```

| Endpoint | Description |
|---|---|
| `/health` | Health check (Docker `HEALTHCHECK` and Kubernetes probes) |
| `/info` | Pod name, node, CPU architecture, version and UTC time |
| `/metrics` | Prometheus metrics (requests, latency, status codes) |
| `/docs` | Interactive API docs (Swagger) |

## Architecture

### CI/CD pipeline

<img src="docs/diagrams/en/02-pipeline.svg" alt="CI/CD pipeline: quality checks and k3s E2E on pull requests; build, scan, sign and GitOps on main" width="100%">

<sub><a href="https://raw.githubusercontent.com/EA-etn/devsecops-pipeline/main/docs/diagrams/en/02-pipeline.png">🔍 View full size</a></sub>

### Supply chain security

<img src="docs/diagrams/en/03-supply-chain.svg" alt="Supply chain: prevention, build, scan and sign, publish and verify" width="100%">

<sub><a href="https://raw.githubusercontent.com/EA-etn/devsecops-pipeline/main/docs/diagrams/en/03-supply-chain.png">🔍 View full size</a></sub>

### Kubernetes deployment

<img src="docs/diagrams/en/04-kubernetes.svg" alt="Kubernetes: ingress, service, deployment and pods across a Raspberry Pi and a PC" width="100%">

<sub><a href="https://raw.githubusercontent.com/EA-etn/devsecops-pipeline/main/docs/diagrams/en/04-kubernetes.png">🔍 View full size</a></sub>

> The diagrams are code: HTML + [Lucide](https://lucide.dev) icons, exported to animated SVG.
> See [`docs/diagrams/src`](docs/diagrams/src).

## Verify an image

Anyone can check that an image was built by this pipeline and was not tampered with:

```bash
cosign verify ghcr.io/ea-etn/demo-api:0.4.0 \
  --certificate-identity-regexp '^https://github.com/EA-etn/devsecops-pipeline/\.github/workflows/ci\.yml@refs/(heads/main|tags/v.*)$' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

<details>
<summary><b>More: SBOM, security controls and quality gate</b></summary>

Inspect the SBOM:

```bash
docker buildx imagetools inspect ghcr.io/ea-etn/demo-api:0.4.0 --format '{{ json .SBOM }}'
```

| Control | Tool | When |
|---|---|---|
| Dependency vulnerabilities | Trivy (`fs`) | Every PR and push |
| Leaked secrets | Trivy (`secret`) | Every PR and push |
| Misconfigurations (Dockerfile, Helm) | Trivy (`misconfig`) | Every PR and push |
| Image vulnerabilities | Trivy (`image`) | PR (local image) and `main` (published image) |
| Software bill of materials | BuildKit (SPDX) | Every published image |
| Build provenance | BuildKit (SLSA) | Every published image |
| Image signature | Cosign keyless (Sigstore) | Every published image |
| Dependency updates | Dependabot (pip, actions, docker) | Weekly |

Findings are published to **Security → Code scanning**. The pipeline **fails** on any fixable
HIGH/CRITICAL finding.

</details>

## Kubernetes & GitOps

<details>
<summary><b>Run it on a local k3s cluster</b> (Docker, <a href="https://k3d.io">k3d</a> and Helm)</summary>

```bash
make cluster          # 3-node k3s cluster
make deploy           # build + import + helm install
make helm-test        # /health, /info and /metrics from inside the cluster
make cluster-delete
```

</details>

<details>
<summary><b>Deploy with ArgoCD</b> (homelab)</summary>

After each merge to `main`, the `gitops` job writes the exact image tag (`sha-xxxxxxx`) to
`chart/demo-api/values-homelab.yaml`. ArgoCD notices the change in Git and deploys it:
**nobody needs cluster access to deploy.**

The ArgoCD `Application` lives in the cluster repo, [homelab-k3s](https://github.com/EA-etn/homelab-k3s) (`apps/demo-api.yaml`),
managed with the App of Apps pattern alongside monitoring and alerting.

| Situation | What ArgoCD does |
|---|---|
| Merge to `main` | Deploys the new version |
| Someone edits the cluster by hand | Reverts it (`selfHeal`) |
| A resource is removed from the chart | Deletes it (`prune`) |
| Need to roll back | `git revert` → ArgoCD deploys the previous version |

</details>

<details>
<summary><b>Releases and image tags</b></summary>

Publish a release from GitHub (**Releases → Draft a new release**, tag `vX.Y.Z`).

| Event | Image tags |
|---|---|
| Pull request | (not published) |
| Push to `main` | `main`, `sha-xxxxxxx` |
| Tag `v1.2.3` | `1.2.3`, `1.2`, `sha-xxxxxxx` |

</details>

<details>
<summary><b>Project structure</b></summary>

```
.
├── app/                         # FastAPI application
├── tests/                       # pytest
├── chart/demo-api/              # Helm chart
│   ├── values.yaml              #   defaults
│   └── values-homelab.yaml      #   homelab environment (updated by GitOps)
├── docs/diagrams/               # Animated architecture diagrams (+ source)
├── docs/lessons-learned.md      # Every incident: root cause and fix
├── .github/workflows/ci.yml     # The whole CI/CD pipeline
├── .github/dependabot.yml       # Automatic updates
├── Dockerfile
└── Makefile
```

</details>

## Lessons learned

Thirteen real incidents came up while building this, each written up with its root cause and fix.
Five that changed how the project works:

| What broke | What it taught |
|---|---|
| A **new HIGH CVE** appeared in `apt` hours after a pull request passed | The gate did its job on `main`: the image was **neither signed nor deployed**. Scanning only at PR time is not enough |
| Days later, new CVEs in `zlib` even though the image runs `apt-get upgrade` | The build cache had frozen that layer. **A cache needs an expiry**: the layer now rebuilds daily |
| Pods ended in `Error` on every rollout. The fix passed CI but **failed on the real cluster** | The node's security policy denied what CI allowed. **CI is not production**: a test now simulates that restriction |
| After each rollout, both replicas landed on the **same node** | The spread rule also counted the pods being replaced. One line fixed it: `matchLabelKeys: [pod-template-hash]` |
| The GitOps bot was **blocked by branch protection** | It now pushes with a deploy key scoped to this repo: **least privilege**, with no admin token |

**→ [All 13, with root cause and fix](docs/lessons-learned.md)** · [infographic](docs/diagrams/en/05-incidents.png)

## Roadmap

- [x] Secure CI/CD pipeline with multi-arch, signed images
- [x] Helm chart tested on k3s in every pull request
- [x] Zero-downtime rollouts: graceful shutdown proven with continuous traffic in CI
- [x] Homelab k3s cluster (Raspberry Pi + PC) with ArgoCD → [homelab-k3s](https://github.com/EA-etn/homelab-k3s)
- [x] Observability: Prometheus, Grafana, SLOs and alerts with runbooks → [homelab-k3s](https://github.com/EA-etn/homelab-k3s)
- [x] Dead man's switch and automatic rebalancing across nodes → [homelab-k3s](https://github.com/EA-etn/homelab-k3s)
- [ ] Chaos engineering on the homelab (in progress)
- [ ] Rebuild the homelab from scratch with Ansible (code ready, real rebuild pending)
- [ ] Cloud infrastructure with Terraform

## License

[MIT](LICENSE)
