# First-tier coding languages: Python, JavaScript and Java

The first tier supports Python, JavaScript and Java. Additional languages and external execution services are deferred.

**Status:** accepted — coding language set and isolation. Harness details and image maintenance remain open.

## Consequences

- Three runtime images, compile paths and per-language harnesses must be maintained and patched.
- The public language list is exactly these three; internal aliases do not expand the promise.
- UI, API and report language labels must match the supported set.
- Adding a language later requires a new decision, image hardening and harness tests.
- Language-specific test harnesses must not leak hidden cases or allow host access.
- Operational cost scales with image size and execution concurrency, not just language count.
