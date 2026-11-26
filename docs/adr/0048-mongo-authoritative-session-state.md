# MongoDB is authoritative for interview session state

The canonical session snapshot and transcript live in MongoDB and are the source of truth. State is checkpointed at least per turn. Redis holds only short-lived device leases, hot cache entries, and wake-up signals; losing Redis must not lose a session. An append-only event collection records state transitions for audit, and the snapshot stores the last applied sequence. MongoDB must run as a replica set because session writes and outbox records commit together in one transaction.

**Status:** accepted — session state ownership and durability. Index names and retention values remain configuration.

## Consequences

- Standalone MongoDB is not a supported production configuration for the engine.
- Resume reloads the Mongo snapshot, not Redis state.
- Device leases use a fencing token checked by repository updates.
- Redis eviction or loss causes degraded latency, not data loss.
- Per-turn checkpoints make practice resume exact and formal recovery auditable.
- Events support audit and recovery checks; the snapshot remains the authoritative read model.
