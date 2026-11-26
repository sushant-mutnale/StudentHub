# Private S3-compatible object storage for files and media

Resumes, formal audio and report assets use private S3-compatible object storage with short-lived signed access and lifecycle policies matching retention classes.

**Status:** accepted — storage model. Provider, bucket layout and encryption keys remain open.

## Consequences

- No application data is written to the local filesystem in production.
- Buckets are private; access is through short-lived signed URLs, not public objects.
- Lifecycle rules enforce retention per data class and delete expired objects.
- Object keys are opaque and do not contain candidate PII.
- Upload validation and malware scanning happen before the object is trusted.
- Provider choice and key management remain open, but the S3-compatible interface is fixed.
