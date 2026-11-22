# Code execution uses a dedicated sandbox worker with ephemeral containers

Code runs on a dedicated sandbox worker, separate from the API and evaluation workers. Each run uses an ephemeral hardened container with no network, read-only root, CPU/memory/PID/time limits, and no host mounts. The sandbox receives visible tests only. Hidden tests run exactly once at formal submission in the trusted evaluator and never enter the sandbox. The first-tier languages are Python, JavaScript, and Java with function-based tasks.

**Status:** accepted — execution boundary and runtime class. Container image, harness, and per-language runtime details remain open.

## Consequences

- The API never executes candidate code in-process or in its own pod.
- The execution workload has its own node pool, scaling, and quotas.
- The trusted evaluator is a separate trusted workload; candidate code reaches it through a controlled handoff, never with hidden-test fixtures.
- Execution is job-based; short runs may return inline and slower runs return a run id for polling.
- Code, outputs, test results, runtime version, and execution evidence persist with the turn.
- Multi-file projects and measured asymptotic complexity remain deferred.
- Runtime image and harness choices must satisfy the isolation and language requirements above.
