# Deployment direction: Docker Compose for development, Kubernetes for production

Development, testing and CI run the full stack (frontend, backend, workers, MongoDB, Redis and other self-hostable supporting services) through Docker Compose, reusing the same application images that production runs. Production uses Kubernetes so application services and workers can be deployed and scaled independently, with MongoDB and Redis self-hosted rather than consumed as managed Atlas/ElastiCache offerings. Vercel serverless and Render remain historical/optional paths, not the production deployment model.

**Status:** accepted — implemented for the production security foundation.

## Considered options

- **Vercel serverless (current repo default).** Rejected as the production model: in-process workers and startup ingestion, local filesystem uploads/audio/sandbox artifacts, WebSocket voice, the Docker-based code sandbox, and `Mangum(app, lifespan="off")` are incompatible with serverless execution.
- **Render / single-PaaS.** Rejected as the target model: the current `gunicorn -w 4` start command runs startup hooks (and therefore workers) in every worker process.
- **Docker Compose only.** Rejected for production because it does not give independent scaling, rolling deploys or self-healing for the worker fleet.

Managed Kubernetes versus self-managed control plane, in-cluster versus separate MongoDB/Redis, cluster sizing, workload, provider and budget are deliberately **not** decided here.

## Consequences

- Serverless-specific assumptions must eventually be removed or isolated; startup side effects (index creation, seeding, worker registration, ingestion) become explicit jobs or separate deployments.
- Background workers must be separate deployables with singleton/cron semantics; they must never start once per web replica.
- Uploads, generated audio and sandbox artifacts need shared object storage or persistent volumes; local disk is not durable across pods.
- The voice WebSocket needs an ingress/proxy that supports long-lived connections; the code sandbox needs an isolated runtime, not a sidecar in the API pod.
- CI must build the same images used in production and run integration tests against Compose services.
- Two divergent requirement sets and three Python versions (Docker 3.10, CI 3.12, Render 3.13) must be reconciled before images are trustworthy.
