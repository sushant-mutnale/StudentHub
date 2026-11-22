# Async work uses a Mongo transactional outbox with atomic claim

Domain state changes and outbox records commit in one MongoDB transaction. Workers claim records with an atomic lease and bounded attempts, then process them idempotently by event id. Delivery is at-least-once. Redis may wake workers but never owns delivery state. Failed records back off and eventually move to a dead-letter state with an operator-visible reason. A worker does not publish before claiming.

**Status:** accepted — async delivery boundary. Broker adoption is deferred.

## Consequences

- MongoDB must be a replica set for transaction support.
- Event and outbox ids are unique; consumers must tolerate duplicate delivery.
- Worker registration happens once in the worker process, never in the API process.
- Deadline/expiry and retention sweeps are registered handlers with the same reliability rules.
- Outbox lag, retry counts, and dead-letter volume are first-class metrics.
- No external message broker is required for the first tier.
