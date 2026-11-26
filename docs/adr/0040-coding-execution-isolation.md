# Coding execution is per-run isolated and separate from the API

Each run uses an isolated environment with no network, read-only root, CPU/memory/PID/time limits, an ephemeral workspace and no host mounts. Execution runs as a separate workload from the API and never exposes hidden tests.

**Status:** accepted — isolation requirements. Runtime class is a dedicated worker with ephemeral containers per ADR 0052; image, harness, and per-language details remain open.

## Consequences

- Code execution must not happen inside the API process or pod.
- The execution service has no host Docker socket, no shared writable volume and no network path to internal services.
- Per-run quotas are enforced outside the candidate's code.
- Hidden test inputs, fixtures and per-case outputs never leave the execution boundary.
- Execution results and logs are returned through a narrow, validated API.
- Runtime choice (containers, microVMs or an external service) remains a later decision against these requirements.
