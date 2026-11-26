# Hybrid voice: browser speech for practice, server-side capture for formal assessments

Practice interviews use browser speech recognition and synthesis with an explicit degraded mode when unsupported. Formal assessments use a server-side real-time voice pipeline that captures audio, produces the authoritative transcript, and enforces controlled turn-taking. Speech processing location is therefore a property of the session mode, not a global voice stack.

**Status:** accepted — voice mode split and recording retention. Provider remains open; formal transport is WebSocket per ADR 0051.

## Consequences

- Two voice paths must be supported and tested; the practice path must degrade visibly, never fabricate transcript text.
- Formal reports may only cite the server-captured transcript and must record consent for audio capture.
- Formal assessments sacrifice natural barge-in for controlled turns and auditable capture; practice may allow interruptions.
- Voice media runs as a separate workload from the API and evaluation workers.
- Server-side capture introduces retention, deletion and access-control requirements for audio and transcripts.
- No speech vendor is selected by this decision.
