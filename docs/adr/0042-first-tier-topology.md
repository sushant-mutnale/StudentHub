# First-tier topology: single-region managed Kubernetes

Production uses single-region managed Kubernetes with separate deployments for API, workers, voice media, and code execution. MongoDB and Redis are self-hosted. Multi-region active-active is deferred.

**Status:** accepted — topology, workload placement, data placement, ingress and storage. Observability remains open.

## Consequences

- The control plane is managed; the team owns workloads, data services and cluster configuration.
- API, workers, voice media and code execution scale independently and are not co-located by default.
- Untrusted code execution never shares a pod or node pool with the API.
- MongoDB/Redis run as stateful services with their own backup, upgrade and failure strategy.
- Single-region means a regional outage is a full outage; the SLO must say so.
- Multi-region is a later decision, not a hidden assumption in the data model.
