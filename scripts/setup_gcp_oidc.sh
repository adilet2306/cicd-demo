#!/usr/bin/env bash
# One-time setup. Run as a GCP administrator, not from the CI workflow.
set -euo pipefail

: "${GCP_PROJECT_ID:?Export GCP_PROJECT_ID}"
: "${GITHUB_REPOSITORY_ID:?Export numeric GITHUB_REPOSITORY_ID}"
: "${GITHUB_OWNER_ID:?Export numeric GITHUB_OWNER_ID}"

[[ "$GITHUB_REPOSITORY_ID" =~ ^[0-9]+$ ]]
[[ "$GITHUB_OWNER_ID" =~ ^[0-9]+$ ]]

POOL_ID=kaizen-github
PROVIDER_ID=github
SA_NAME=kaizen-cicd-deployer
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')
SA_EMAIL="$SA_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"

gcloud services enable iam.googleapis.com iamcredentials.googleapis.com \
  sts.googleapis.com container.googleapis.com --project="$GCP_PROJECT_ID"

gcloud iam service-accounts create "$SA_NAME" --project="$GCP_PROJECT_ID" \
  --display-name='Kaizen CI/CD namespace deployer'

gcloud iam workload-identity-pools create "$POOL_ID" \
  --project="$GCP_PROJECT_ID" --location=global \
  --display-name='Kaizen GitHub Actions'

gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --project="$GCP_PROJECT_ID" --location=global \
  --workload-identity-pool="$POOL_ID" \
  --issuer-uri='https://token.actions.githubusercontent.com' \
  --attribute-mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id' \
  --attribute-condition="assertion.repository_id == '$GITHUB_REPOSITORY_ID' && assertion.repository_owner_id == '$GITHUB_OWNER_ID' && assertion.ref == 'refs/heads/main' && assertion.event_name == 'push'"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$GCP_PROJECT_ID" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/attribute.repository_id/$GITHUB_REPOSITORY_ID"

# Fetch cluster metadata; Kubernetes write permissions are granted separately by RBAC.
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" --role=roles/container.clusterViewer \
  --condition=None

printf '\nGitHub repository variables:\nGCP_PROJECT_ID=%s\nGCP_SERVICE_ACCOUNT=%s\nWIF_PROVIDER=projects/%s/locations/global/workloadIdentityPools/%s/providers/%s\n' \
  "$GCP_PROJECT_ID" "$SA_EMAIL" "$PROJECT_NUMBER" "$POOL_ID" "$PROVIDER_ID"
