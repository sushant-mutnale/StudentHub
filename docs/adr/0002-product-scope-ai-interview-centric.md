# Product scope: AI interview-centric career development platform

StudentHub is not a generic job board with an interview feature bolted on. The AI interview experience is the product: students move from signup and profile/resume through target role, interview preparation, AI interview, evaluation, skill-gap analysis, learning recommendations and progress tracking into subsequent interviews. Text, voice, coding/DSA, orchestrated task workers, transcripts, structured evaluation, skill-gap analysis and cross-interview progress are first-class production capabilities, not experiments. ADR 0047 retires the legacy multi-agent loop as the conversational owner while preserving task orchestration through the canonical engine's worker ports.

**Status:** accepted — product scope. Detailed product decisions are recorded in ADRs 0003–0046; remaining open items are tracked in requirements.

## Module rule

No existing module is removed or labelled experimental without first mapping it to the interview journey or to another explicit product responsibility. Supporting capabilities (auth, resume, jobs, learning, notifications, admin, recruiter/ATS, social) remain in scope as enablers until their contribution and production cost are understood.

## Consequences

- Session persistence, transcript durability, evaluation integrity and recovery are core domain problems, not infrastructure details.
- The current split between the fully persisted structured interview path and the multi-agent path must converge; interviews cannot lose their transcript and report when Redis TTL expires.
- Failure, retry, concurrency and resumability semantics must be defined per interview mode (text, voice, coding).
- Supporting modules are prioritised by how directly they serve the interview journey; recruiter/ATS and social are evaluated for retention, not assumed to ship in the first production milestone.
- "Production-ready" means the complete student journey survives restarts, provider failures and concurrent use — not that endpoints respond in isolation.
