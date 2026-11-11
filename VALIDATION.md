# Validation performed before delivery

- Python 3.12: all 12 application tests passed.
- Ruff: application, tests, and Python helper scripts passed.
- Runtime lock: all eight packages reinstalled successfully with pip --require-hashes.
- pip-audit: no known vulnerabilities returned for the runtime lock at validation time.
- Runtime license check: all eight packages passed the supplied classroom allowlist.
- Negative license checks: UNKNOWN and GPL-3.0-only values were rejected.
- Kubeconform: all five resources in the three source manifests passed strict validation.
- Rendered Deployment and Service passed validation; invalid string replicas were rejected.
- Actionlint v1.7.12: workflow syntax and GitHub expressions passed (shellcheck disabled).
- OIDC setup Bash script passed bash -n syntax validation.
- HTTP smoke test passed against a locally started two-worker Gunicorn server: health,
  expected release version, greeting, and addition.

Not run here: Docker build or Trivy container-image scan (no Docker engine in this environment),
GitHub-hosted workflow execution, Google IAM setup, GKE deployment, or environment approval.
Those require your repositories, registry token, GCP configuration, and cluster access.
Dependency/image vulnerability results can change as packages and databases change.
Schema checks do not substitute for a live cluster rehearsal.
