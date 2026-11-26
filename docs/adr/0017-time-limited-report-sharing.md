# Formal reports are shared through time-limited anonymous links

Formal reports are shared through links that expire after 90 days by default, can be renewed while the report is retained (up to 1 year), are revocable at any time, and log access time and IP/user agent. Viewers do not need an account. PDF export is optional, not the only sharing mode.

**Status:** accepted — sharing model. Access-log retention and abuse controls remain open.

## Consequences

- A share token model is required, with per-link expiry, revocation and access logging.
- Link lifetime can never exceed the report's retention period.
- Anonymous access means the system cannot verify viewer identity; reports must not imply otherwise.
- Access logs are candidate-visible and subject to retention/deletion rules.
- Revocation must take effect immediately; cached or exported copies cannot be recalled.
- PDF export must carry the same rubric version, evidence and non-comparability caveats as the hosted report.
