# Secret Rotation Runbook

## When to use

Use this runbook when a tracked environment file, token, key, or credential may be compromised.

## Steps

1. Identify every provider whose credentials appear in the exposed file.
2. Rotate each credential at the provider. Record only the rotation date, not the value.
3. Revoke old sessions or keys where the provider supports revocation.
4. Remove the file from the current tree with `git rm backend/.env.production`.
5. Run `pwsh -File scripts/prepare-secret-purge.ps1` and confirm the dry-run output.
6. Install `git-filter-repo` and run `pwsh -File scripts/prepare-secret-purge.ps1 -Apply` on a dedicated local clone.
7. Verify `git ls-files backend/.env.production` returns no output.
8. Verify `gitleaks detect` returns no findings.
9. Do not force-push rewritten history until explicitly requested.
10. After approved force-push, instruct collaborators to re-clone or hard-reset their branches.

## Prohibited

- Do not paste secret values into issues, pull requests, logs, chats, or commits.
- Do not add `.env.production` to any commit.
- Do not force-push a rewritten branch without explicit approval.

## Production operations

### Required configuration

- `APP_ENV=production` makes startup validation blocking. Set `JWT_SECRET`, `MONGODB_URI`, `REDIS_HOST`, `FRONTEND_ORIGIN`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `LIVEKIT_URL` to real deployment values before starting any image.
- LiveKit defaults (`devkey`, `secret`, and a localhost URL) are rejected in production. Put `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` in the `studenthub-secrets` Secret; set the real `wss://` endpoint in `studenthub-config`.
- MongoDB must run as a replica set. Canonical engine start, turn, and resume writes use multi-document transactions, which a standalone mongod cannot commit.

### Image build

1. Build the web image: `docker build -f Dockerfile -t studenthub-web:latest .`
2. Build the worker/init image: `docker build -f Dockerfile.worker -t studenthub-worker:latest .`
3. Tag and push both images to the deployment registry. Use the same image tags for web, worker, and init jobs.
4. Run the secret scan with the pinned scanner before pushing: `docker run --rm -v "$PWD:/repo" -w /repo gitleaks/gitleaks:v8.30.1 detect --config .gitleaks.toml --redact`

### Compose smoke

1. Build the stack: `docker compose build web worker init-job`
2. Start dependencies and services: `docker compose up -d mongo redis web worker`
3. Wait for `curl -fsS http://localhost:8000/health` to succeed.
4. Run the init job explicitly: `docker compose run --rm init-job`
5. Exercise a real engine write: `docker compose exec -T worker python -m backend.scripts.compose_smoke`
6. Tear down: `docker compose down -v` (destructive; use only with disposable volumes).

### Kubernetes apply order

1. Create the namespace and the `studenthub-secrets` Secret out of band. Never commit the Secret manifest with values.
2. Apply `k8s/base/configmap.yaml` with the real LiveKit, frontend, Redis, and Mongo settings.
3. Apply `k8s/base/services.yaml`.
4. Apply `k8s/base/init-job.yaml`, then wait for `job/studenthub-init` to complete before serving traffic.
5. Apply `k8s/base/web-deployment.yaml` and wait for rollout; check `/health/ready`.
6. Apply `k8s/base/worker-deployment.yaml` and wait for rollout; check `/health/worker` through `service/studenthub-worker-health`.
7. Re-run the Compose engine smoke against the same image tags when the cluster cannot run Compose locally.

### Init-job reruns

1. Re-run indexes and seed/ingestion work with `kubectl create job --from=job/studenthub-init studenthub-init-rerun-<timestamp>`.
2. Wait for the generated Job to complete and inspect its logs for failures without printing secret values.
3. Delete completed rerun Jobs once verified. Do not run the init job from a web pod.

### Worker scaling

1. Scale only the worker Deployment: `kubectl scale deployment studenthub-worker --replicas <n>`.
2. Confirm `/health/worker` reports a fresh heartbeat and a draining outbox; heartbeat failures are retried before the worker loop continues.
3. Scale web replicas independently. Never scale the init Job as a long-running process.

### Backup and restore

1. Back up MongoDB from a replica-set secondary with `mongodump --uri <mongo-uri> --out <timestamped-directory>`; encrypt and store the dump outside the cluster.
2. Back up Redis persistence with the provider snapshot or `BGSAVE`, including the worker heartbeat and lease keys.
3. To restore, stop web and worker traffic, restore Mongo with `mongorestore --uri <mongo-uri> --drop <directory>`, restore the Redis snapshot, re-run the init job, then restart web and worker and repeat the Compose smoke.
4. Verify restored engine sessions, outbox state, and `/health/ready` before reopening traffic.

### Incident response

1. For suspected secret exposure, follow the rotation steps above first, then disable affected LiveKit tokens and revoke provider sessions.
2. Capture operational logs and request IDs only; never paste tokens, cookies, authorization headers, or secret values into tickets.
3. If the secret scan reports a finding outside the reviewed `backend/.env.production` allowlist, treat it as active and rotate that credential.
4. After an authorized history purge, remove the `[[allowlists]]` entry from `.gitleaks.toml` and confirm the scan is clean without it.
5. If Redis leases and persisted `fencing_token` values diverge, pause new resumes, restore the lease from the authoritative Mongo session, and re-run the smoke test before resuming traffic.
