#!/usr/bin/env bash
# Build both images with Cloud Build and roll out the Cloud Run service.
# One-time infrastructure (Cloud SQL, bucket, secrets, service account, IAP) is in deploy/README.md.
set -euo pipefail

PROJECT=${PROJECT:-ai-video-dooinn}
REGION=${REGION:-europe-west9}
TAG=${TAG:-$(git rev-parse --short HEAD)}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPO="$REGION-docker.pkg.dev/$PROJECT/shorts"
SPEC="$(mktemp -d)/service.yaml"

gcloud builds submit "$ROOT/backend" --project="$PROJECT" --tag="$REPO/api:$TAG"
gcloud builds submit "$ROOT/frontend" --project="$PROJECT" --tag="$REPO/console:$TAG"

uv run --project "$ROOT/backend" python "$ROOT/deploy/render.py" \
  --project="$PROJECT" --region="$REGION" --tag="$TAG" --out="$SPEC"
gcloud run services replace "$SPEC" --project="$PROJECT" --region="$REGION"

# IAP in front of every ingress path; only accounts granted iap.httpsResourceAccessor get in.
gcloud run services update shorts --iap --project="$PROJECT" --region="$REGION"
gcloud run services describe shorts --project="$PROJECT" --region="$REGION" --format="value(status.url)"
