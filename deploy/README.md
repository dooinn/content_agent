# Deploying to Google Cloud

One Cloud Run service runs the review console (Next.js, ingress on 8080) with the agent API (FastAPI) as a sidecar on `localhost:8000`. The API is never exposed on its own. Identity-Aware Proxy sits in front of the service, so only granted Google accounts can open the console.

| Resource | Name (project `ai-video-dooinn`, region `europe-west9`) |
|---|---|
| Cloud Run service | `shorts`, scale to zero, max 1 instance, CPU always allocated while up |
| Images | Artifact Registry `shorts/console`, `shorts/api` |
| Checkpoints | Cloud SQL Postgres 17 `shorts-db` (db-f1-micro), database and user `shorts` |
| Assets | GCS bucket `ai-video-dooinn-shorts` (private; the API redirects `/files/*` to signed URLs) |
| Secrets | `anthropic-api-key`, `magnific-api-key`, `elevenlabs-api-key`, `shorts-db-password`, `shorts-database-url` |
| Runtime identity | `shorts-run@` with Cloud SQL Client, Secret Accessor, Log Writer, object admin on the bucket, and Token Creator on itself (to sign URLs) |

Max 1 instance is deliberate: projects run as in-process background tasks. If the instance scales down mid-run, `Retry` resumes from the last LangGraph checkpoint.

## Deploy

```bash
deploy/deploy.sh            # builds both images, renders deploy/service.template.yaml, rolls out
```

`deploy/render.py` copies non-secret settings (models, voice id) from `backend/.env`; API keys stay in Secret Manager.

## One-time setup

1. Enable APIs: Cloud Run, Cloud SQL Admin, Artifact Registry, Secret Manager, IAP, Cloud Build, IAM Credentials, Cloud Resource Manager (needed to grant IAP access).
2. Create the Artifact Registry repository, the bucket, the Cloud SQL instance, database, and user, and the secrets above. `shorts-database-url` is `postgresql://shorts:<password>@/shorts?host=/cloudsql/ai-video-dooinn:europe-west9:shorts-db`.
3. IAP in a project without an organization needs a custom OAuth client:
   1. Google Auth Platform → Branding: create the app, audience **External**, and add your account as a test user.
   2. Clients → Create client → Web application. Add the redirect URI `https://iap.googleapis.com/v1/oauth/clientIds/<CLIENT_ID>:handleRedirect`.
   3. Apply it: `gcloud iap settings set iap_settings.yaml --project=ai-video-dooinn`, with the client id and secret under `access_settings.oauth_settings`.
4. Let IAP call the service and grant access:

```bash
gcloud run services add-iam-policy-binding shorts --region=europe-west9 \
  --member=serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-iap.iam.gserviceaccount.com --role=roles/run.invoker
gcloud iap web add-iam-policy-binding --region=europe-west9 --resource-type=cloud-run --service=shorts \
  --member=user:<you@gmail.com> --role=roles/iap.httpsResourceAccessor
```

## Moving local projects

```bash
gcloud storage rsync backend/data gs://ai-video-dooinn-shorts --recursive     # assets and project index
pg_dump --no-owner --no-acl shorts > checkpoints.sql                          # from the local Postgres
gcloud storage cp checkpoints.sql gs://ai-video-dooinn-shorts/migrations/
gcloud sql import sql shorts-db gs://ai-video-dooinn-shorts/migrations/checkpoints.sql --database=shorts --user=shorts
```
