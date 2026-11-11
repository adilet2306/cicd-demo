# Kaizen: GitHub Actions CI/CD to GKE

A small Flask application and a single workflow with five visible jobs. Designed for
students who already understand Docker, Deployments, probes, Services, RBAC, and GitHub Actions.

## What runs

Pull request to main:

1. Ruff and 12 pytest cases check behavior and invalid input handling.
2. pip-licenses inspects only the isolated runtime environment. A Python script enforces an
   explicit classroom license allowlist; unknown and unapproved values fail.
3. pip-audit checks the hash-locked runtime dependency file for known vulnerabilities.
4. Kubeconform validates the Kubernetes manifests against resource schemas.
5. Docker builds the image. Trivy scans OS and application packages before any publishing.

Push to main runs the same gates, then publishes the exact scanned image to Docker Hub.
The production deployment job obtains short-lived Google credentials through GitHub OIDC,
deploys the image by immutable digest, waits for rollout, and verifies health, commit version,
greeting, and addition through the Service.

No credentials are needed for pull-request checks. No pull_request_target trigger is used.
Actions are pinned to resolved commit SHAs. Runtime dependencies include PyPI artifact hashes.
Developer/auditing tool versions are pinned, but their transitive dependencies are not locked.
The Python base image is a moving maintained tag; its OS packages can change between builds.

## App endpoints

| Request | Result |
|---|---|
| GET / | JSON greeting, commit version, and hostname |
| GET /health | `{"status":"ok"}` |
| POST /api/add with `{"a":2,"b":3}` | `{"result":5}` |
| POST /api/add with invalid input | HTTP 400 |

The browser displays JSON so students can see release identity without frontend dependencies.
Gunicorn serves the container on port 8080; the Flask development server is for local use only.

## 1. Run locally

Use Python 3.12 and a fresh environment. On Windows, activate with `.venv\Scripts\activate`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
python -m pip install -r requirements-dev.txt
ruff check .
python -m pytest -v
python app.py
```

In another terminal:

```bash
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/health
curl -H 'Content-Type: application/json' -d '{"a":2,"b":3}' http://127.0.0.1:8080/api/add
```

Optional local Docker rehearsal:

```bash
docker build -t kaizen-cicd-demo:local .
docker run --rm -p 8080:8080 -e APP_VERSION=local kaizen-cicd-demo:local
```

## 2. Create repositories

Create a GitHub repository (for example `kaizenacademy/cicd-demo`) with default branch `main`.
Create a PUBLIC Docker Hub repository (for example `kaizenacademy/cicd-demo`). Public image
pulls keep this lab independent of Kubernetes imagePullSecrets. Use your own account names.

Copy this directory's CONTENTS into your Git repository, including `.github/`. If unzipping
through a file manager, confirm the workflow directory was copied. Do not commit virtualenvs,
credentials, reports, or kubeconfig files. The supplied gitignore excludes common generated files.

You can push a feature branch and open a PR before configuring CD: PR checks do not need GCP
or Docker Hub secrets. Configure CD before your first push/merge to main intended to deploy.

## 3. Choose how the deployment runner reaches GKE

The existing bastion's access does NOT give GitHub-hosted runners access.

Option A: default `ubuntu-latest` deployment runner. Your GKE API endpoint must be reachable
from that runner, and any endpoint access/authorized-network controls must permit it.
Do not open the API globally just to make this lab pass. Standard GitHub-hosted runner source
addresses are not a single fixed classroom IP.

Option B: a dedicated Linux self-hosted runner VM with private GKE connectivity. Set the
repository variable `DEPLOY_RUNNER` to a unique label such as `kaizen-gke-deploy` and apply that
label to the registered runner. Set `GKE_USE_INTERNAL_IP=true` if the action should select
GKE's internal endpoint. Keep CI jobs on GitHub-hosted runners as supplied. Use a trusted
repository for this exercise, restrict who can change main/workflows, and require deployment
approval. Do not use a shared runner that holds a privileged personal kubeconfig or a broad
GCP VM service-account identity. Use a dedicated VM with a minimally privileged attached
identity (or none); this workflow uses OIDC. Runner installation is under GitHub Settings >
Actions > Runners. It must support Node 24 actions and Python 3.12 setup.

The workflow creates its own temporary kubeconfig. Do not upload your bastion kubeconfig
as a GitHub secret. Deployment scripts assume a Linux runner with Bash and curl.

## 4. One-time Google OIDC setup

Run in Cloud Shell or your admin VM with gcloud authenticated as an administrator with
permission to create service accounts, Workload Identity Federation resources, and IAM bindings.
This is a first-time setup script, not a rerunnable reconciliation script. It creates named
resources; if they exist, inspect/reuse them rather than deleting an existing shared setup.

Find the numeric GitHub IDs (GitHub CLI example, after `gh auth login`):

```bash
gh api repos/YOUR_OWNER/YOUR_REPOSITORY --jq '{repository_id: .id, owner_id: .owner.id}'
```

Export real values and run:

```bash
export GCP_PROJECT_ID=YOUR_PROJECT_ID
export GITHUB_REPOSITORY_ID=YOUR_NUMERIC_REPOSITORY_ID
export GITHUB_OWNER_ID=YOUR_NUMERIC_OWNER_ID
bash scripts/setup_gcp_oidc.sh
```

The provider restricts tokens to those numeric repository/owner IDs and pushes to main.
It grants service-account impersonation, not a permanent JSON key. IAM changes can take
several minutes to propagate. The script prints three values to copy into repository variables.

The script grants cluster metadata access using `roles/container.clusterViewer`. Namespace
write access is granted separately below. No project Editor or Kubernetes cluster-admin role
is assigned to the workflow identity.

## 5. Bootstrap the namespace and deployment permissions

Run as your existing GKE administrator. First list contexts and choose GKE explicitly:

```bash
kubectl config get-contexts
export GKE_CONTEXT=YOUR_GKE_CONTEXT
export DEPLOYER_EMAIL=kaizen-cicd-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com
kubectl --context="$GKE_CONTEXT" apply -f k8s/namespace.yaml
sed "s|SERVICE_ACCOUNT_EMAIL|$DEPLOYER_EMAIL|g" k8s/deployer-rbac.yaml |
  kubectl --context="$GKE_CONTEXT" apply -f -
```

These permissions let the workflow manage this demo's Deployments/Services and open a Pod
port-forward for the smoke test. They do not grant namespace creation or access to Secrets.
Kubeconform is schema validation, not proof that admission, networking, capacity, or rollout
will succeed. Deployment commands provide the real cluster validation.

## 6. Configure GitHub

Settings > Secrets and variables > Actions > Variables:

| Variable | Example |
|---|---|
| IMAGE_REPOSITORY | `kaizenacademy/cicd-demo` (your public Docker Hub repo) |
| DOCKERHUB_USERNAME | `kaizenacademy` |
| GCP_PROJECT_ID | your GCP project ID |
| GKE_CLUSTER | your cluster name |
| GKE_LOCATION | cluster region or zone, e.g. `us-central1-a` |
| WIF_PROVIDER | full provider resource name printed by setup |
| GCP_SERVICE_ACCOUNT | service-account email printed by setup |
| DEPLOY_RUNNER | optional; default `ubuntu-latest`, or your dedicated runner label |
| GKE_USE_INTERNAL_IP | optional; `true` for private endpoint routing, otherwise `false` |

Settings > Secrets and variables > Actions > Secrets:

| Secret | Value |
|---|---|
| DOCKERHUB_TOKEN | Docker Hub access token with push access to the demo repo |

Settings > Environments: create `production`. Configure required reviewers if available for
your repository visibility and GitHub plan. The workflow only requests the environment;
it does not create its approval rules. Without required reviewers deployment is automatic.
Docker Hub publishing happens before this environment gate, so its token is a repository secret.

Protect main: require a pull request and the four check results: Lint and unit tests;
Dependencies and licenses; Kubernetes manifest validation; Build, scan, and publish.
Require reviews for workflow changes. Branch protection/ruleset availability depends on plan.

## 7. Push and demonstrate

```bash
git init -b main
git add .
git commit -m 'Add tested application and GKE delivery pipeline'
git remote add origin https://github.com/YOUR_OWNER/YOUR_REPOSITORY.git
git push -u origin main
```

The first main push runs the whole pipeline. Open GitHub Actions, inspect the jobs, and approve
the production environment when prompted. Download JSON/XML reports under workflow artifacts.
Then make lesson changes on branches and use PRs.

Inspect the rollout from your admin VM:

```bash
kubectl --context="$GKE_CONTEXT" -n cicd-demo get deployments,pods,services
kubectl --context="$GKE_CONTEXT" -n cicd-demo get deployment cicd-demo \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Browser access from your laptop (with working GKE credentials):

```bash
kubectl --context="$GKE_CONTEXT" -n cicd-demo port-forward service/cicd-demo 8080:80
```

Open http://localhost:8080. If using a remote VM, use an SSH tunnel to that VM's local forwarded
port; localhost on the VM is different from localhost on the laptop. Cloud Shell can use Web
Preview on 8080. This basic JSON application does not load Grafana-style JavaScript bundles.

## 8. Teaching demos (restore each change before the next one)

| Demo | Change | Expected result |
|---|---|---|
| Unit test failure | In app.py change `a + b` to `a - b` | Addition tests fail; image job is skipped |
| Lint failure | Add `import math` without using it | Ruff F401; image job is skipped |
| License failure | Temporarily remove `BSD-3-Clause` and `BSD License` from ALLOWED | Runtime license check fails |
| Manifest failure | Change replicas from `2` to `"two"` | Kubeconform rejects the schema |
| Successful release | Restore everything; make a harmless comment change; merge | New image digest and commit version are deployed |
| Readiness failure | In readinessProbe ONLY change /health to /missing | CI schema passes; deployment rollout times out |

For a visible greeting change update BOTH the greeting assertion in tests/test_app.py AND the
expected greeting in scripts/smoke_test.py along with app.py. A comment-only change is an easier
first success demo: the displayed commit version still changes automatically.

For dependency/image vulnerability demos, prepare and scan an old dependency/base-image
revision during rehearsal. Vulnerability databases change; do not rely on a fixed historical
package always having the same findings. Do not deploy the vulnerable rehearsal revision.
Do not bypass the normal hash lock by casually editing just a version line: regenerate the
complete dependency lock and hashes when updating dependencies.

To update the lock, edit requirements.in, then use a separate Python 3.12 maintenance venv
with pip-tools installed and run `pip-compile --generate-hashes --output-file=requirements.txt
requirements.in`. Review the resulting changes, reinstall in a clean environment, and rerun
the checks. Regeneration can change transitive packages and license metadata.

## 9. Rollback demo

After a readiness failure, existing ready Pods may continue serving during the rolling update.
The workflow fails; Kubernetes does not automatically roll back because rollout status timed out.
From your administrator session:

```bash
kubectl --context="$GKE_CONTEXT" -n cicd-demo rollout history deployment/cicd-demo
kubectl --context="$GKE_CONTEXT" -n cicd-demo rollout undo deployment/cicd-demo
kubectl --context="$GKE_CONTEXT" -n cicd-demo rollout status deployment/cicd-demo
```

Rollback requires an earlier working revision. Revert the bad Git change afterward so the next
pipeline does not reintroduce it. A post-deployment smoke failure also does not auto-rollback.
The smoke test verifies a selected Service backend after all Deployment replicas have rolled
out; it is not an exhaustive per-Pod or external-Ingress end-to-end test.

## Scan policies and limits

- Dependency audit: fail on any known runtime dependency vulnerability returned by pip-audit.
- Image scan: save a full vulnerability JSON report, but gate only HIGH/CRITICAL findings with
  available fixes (`--ignore-unfixed` for the gate). Unfixed findings remain visible in the report.
- License policy: classroom exact-value allowlist; no legal conclusions. Compound or unknown
  license values require review. Only installed runtime Python packages are included, not OS licenses.
- Schema validation: built-in Kubernetes objects only in this lab; no CRD schema installation.
- Scans require network access and databases. Scanner or database errors fail the job.
- No scan guarantees security. No secret scanner, SAST, DAST, or load test is included.
- Pip audit and license checks do not scan developer/auditing tools themselves.

## Cleanup

Using the correct GKE context, delete only this lab namespace:

```bash
kubectl --context="$GKE_CONTEXT" delete namespace cicd-demo
```

Disable/remove the GitHub workflow before further main pushes. Unregister any dedicated runner
and remove its VM when finished. Remove this lab's OIDC provider/pool, service account, and IAM
bindings only after confirming they are unused elsewhere. Docker Hub images and GitHub artifacts
have independent retention; namespace deletion does not remove them.

## Primary references

- https://github.com/google-github-actions/auth
- https://github.com/google-github-actions/get-gke-credentials
- https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
- https://github.com/pypa/pip-audit
- https://github.com/raimon49/pip-licenses
- https://github.com/aquasecurity/trivy
- https://github.com/yannh/kubeconform
- https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
