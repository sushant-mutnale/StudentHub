# First-tier coding interviews: function-based tasks with visible practice tests and hidden formal tests

Coding interviews use a small declared language set and function-based tasks. Practice sessions expose visible tests and run/test controls; formal assessments add hidden tests. Candidates state complexity and justify it, with optional scaling probes; complexity is not presented as measured. Code, test results and execution evidence are persisted. Multi-file projects, debugging/code-review tasks and measured asymptotic complexity are deferred from the first production milestone; they remain in the specification.

**Status:** accepted — coding scope, languages, test split, and isolation. Harness, persistence and runtime remain open.

## Consequences

- Practice and formal coding sessions share a task model but differ in test visibility and run/test permissions.
- Hidden tests must never leak through API responses, logs or execution output.
- Execution runs as a separate workload with its own scaling and quotas; it is not a Docker CLI inside the API pod.
- Code and results become part of the session record and are subject to retention, deletion and assessment audit rules.
- Deferred coding types must remain representable in the type model.
