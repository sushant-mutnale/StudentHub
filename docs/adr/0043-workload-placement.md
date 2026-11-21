# Separate node pools by workload class

Production uses separate node pools for general API/workers, latency-sensitive voice media, untrusted code execution, and stateful data services, with independent scaling and taints/tolerations.

**Status:** accepted — node-pool separation. Node sizes and autoscaling remain open.

## Consequences

- The sandbox never shares a node pool with the API or voice media.
- Voice media scales on latency/concurrency signals, not general CPU.
- Data services are isolated from application workload churn.
- Taints, tolerations and anti-affinity are required, not optional scheduling hints.
- Each pool needs its own capacity and cost monitoring.
- A single pool outage should not take down every workload class.
