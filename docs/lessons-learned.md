# Lessons learned

**English** · [Español](lessons-learned.es.md)

Every real incident hit while building this project: what broke, why, and what changed so it
does not happen again. The six with the most to teach are also an
[infographic](diagrams/en/05-incidents.png).

They are in the order they happened.

| # | Problem | Root cause | Fix |
|---|---|---|---|
| 1  `docker build` fails with **429 Too Many Requests** | Docker Hub anonymous pull limit | Pull the base image from a mirror (`mirror.gcr.io`) |
| 2  `pip` fails inside the build: *certificate verify failed* | A corporate proxy intercepts HTTPS | Inject the proxy CA **only** in a local build stage, never in the final image |
| 3  `trivy-action` fails to install Trivy | Its install script could not download the binary | Run the official Trivy image **pinned by digest** (also more secure) |
| 4  Rolling update fails: *annotations: expected string* | The chart did not quote numeric annotations | `quote` in the template, caught by the k3s E2E test |
| 5  Trivy and Cosign fail on `main`: *could not parse reference* | `github.repository` keeps uppercase (`EA-etn`); Docker needs lowercase | Normalize with `${IMAGE,,}`. Steps that only run on `main` need coverage too |
| 6  A release does not trigger the pipeline | The tagged commit contained the **skip-CI** marker; GitHub also reads it from PR titles in merge commits | Drop the marker from the bot commit (`GITHUB_TOKEN` pushes never trigger workflows) and keep it out of PR titles |
| 7  `main` fails right after a merge: Trivy finds a **new HIGH CVE** in `apt` | Disclosed hours after the PR passed; the official base image was not patched yet | `apt-get upgrade` in the final stage. The gate worked: the image was neither signed nor deployed |
| 8  The GitOps bot cannot push: `GH013 Repository rule violations` | The `main` ruleset requires status checks, and `GITHUB_TOKEN` cannot bypass it | The bot pushes with an SSH **deploy key** listed as a ruleset bypass; `paths-ignore` stops its commit from re-triggering the pipeline |
| 9  Pods end in `Error` when they shut down during a rolling update | Uvicorn ≥ 0.29 re-raises `SIGTERM` after a clean shutdown: exit code 143 | `app/serve.py` exits with 0, plus a `preStop` sleep so the Ingress stops routing first. CI proves 0 failed requests during a rollout |
| 10  The fix passed CI and local Docker, but in the homelab pods still ended in `Error` (exit 1) | Uvicorn re-raises the signal with `signal.raise_signal()`, and the node's security policy (most likely AppArmor) denies it: `PermissionError` | A `uvicorn.Server` subclass that never re-raises the signal. A test now simulates that restriction. Lesson: CI and production are not the same environment, so check the real exit code and logs |
| 11  `main` and PRs fail days later: Trivy finds **new HIGH CVEs** in `zlib` even though the image runs `apt-get upgrade` | The BuildKit cache in GitHub Actions reused the old `apt-get upgrade` layer: the command text never changed, so the patches never arrived | The CI passes today's date as a build argument (`APT_CACHE_BUST`), so that layer is rebuilt at least once a day. A cache must have an expiry |
| 12  After every rollout, **both replicas end up on the same node** even though both nodes are healthy | The spread rule (`ScheduleAnyway`) also counted the old pods that were about to be terminated, so the new ones looked balanced while landing on the same node | `matchLabelKeys: [pod-template-hash]`: only pods of the same revision are counted. Spotted in the homelab with `/info`, the Pi ruled out first (`Ready`, no taints or pressure) |
| 13  After rebooting the laptop worker, **both replicas stayed on the Raspberry Pi** | Kubernetes evicted the pod from the unreachable node after ~5 min and recreated it on the Pi; when the node came back nothing moved it, because the scheduler only places pods when they are created, and the spread rule was only a preference | In the homelab the spread rule is mandatory (`DoNotSchedule`) with `nodeTaintsPolicy: Honor`, so a down node does not block new pods. The [Descheduler](https://github.com/EA-etn/homelab-k3s/blob/main/apps/descheduler.yaml) then moves a pod back within 5 minutes of the node returning |

## What they have in common

- **A check that only runs in one place is a blind spot.** Three incidents (#5, #6, #10) passed
  every pull request and failed on `main`, on a release tag or on the real cluster.
- **Security gates earn their keep after the merge.** Twice (#7, #11) a CVE appeared in code that
  had not changed. Both times the image was neither signed nor deployed.
- **Defaults are opinions.** A cache that never expires (#11), a spread rule that is only a
  preference (#12, #13): each default was reasonable until the day it was not.
