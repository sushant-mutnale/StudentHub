# Self-hosted MongoDB and Redis run on dedicated VMs outside Kubernetes

MongoDB and Redis run on dedicated VMs outside Kubernetes, on a private network, with automated backups and independent recovery.

**Status:** accepted — data-service hosting. Replication, backup and failover design remain open.

## Consequences

- The data tier has its own patching, backup and failover procedures; it is not managed by Kubernetes.
- Applications connect over a private network with authenticated, encrypted connections.
- Stateful data is not scheduled onto application node pools.
- A cluster outage and a data-tier outage are separate failure domains with separate recovery steps.
- Capacity planning and cost tracking for the data tier are separate from the cluster.
- Managed database services remain excluded by the self-hosting decision.
