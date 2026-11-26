# Class-based retention defaults

Retention is defined per data class. Practice audio is not stored by default; formal audio is kept 30 days. Raw practice transcripts are kept 90 days; formal transcripts and reports 1 year. Competency summaries are kept until deletion or 2 years. Analytics use de-identified data only. Deletion completes within 30 days including derived data, with backups purged within 90 days.

**Status:** accepted — retention defaults and deletion SLA. Legal holds, export format and jurisdiction overrides remain open.

## Consequences

- Every stored item needs a retention class and an expiry timestamp.
- Formal-report evidence must survive long enough to support disputes; audio expires sooner than the report.
- Deleting a transcript must also delete derived caches, indexes and projections within the same SLA.
- Backup purging is a separate, verifiable process; "deleted" is not claimed until backups expire.
- Retention durations may be overridden per jurisdiction, but the classes stay stable.
- De-identified analytics must be irreversible and must not retain raw content.
