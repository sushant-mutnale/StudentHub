# Formal voice uses WebSocket streaming; practice uses browser speech

Practice voice remains browser speech with a visible degraded mode, as decided in ADR 0011. Formal assessments stream audio over a dedicated WebSocket voice-media deployment to server-side STT/TTS adapters. The server transcript is authoritative for formal assessment. Transcribed answers use a typed transcript contract with source and finality; partial transcripts never create turns. WebRTC is deferred. The STT/TTS provider remains open.

**Status:** accepted — formal voice transport. Provider, endpointing thresholds, and assessment audit signals remain open; owner-scoping, candidate visibility, and access logging for formal audio are required.

## Consequences

- Two voice paths must be tested: browser speech for practice, server capture for formal.
- Practice failure switches visibly to text; formal failure continues in text with a recorded mode change.
- Formal audio is opt-in, owner-scoped, candidate-visible, access-logged, and retained for 30 days.
- Voice media uses a dedicated ingress and separate deployment from the API.
- Formal turn-taking is controlled with explicit cues and no barge-in.
- No speech provider is selected by this decision.
