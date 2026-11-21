# Separate ingress paths for API and voice media

API HTTP/WebSocket traffic uses the standard ingress. Voice media uses a dedicated low-latency ingress/load balancer so long-lived voice connections do not share timeouts or failure modes with ordinary API traffic.

**Status:** accepted — ingress separation. Ingress provider and voice transport remain open.

## Consequences

- API and voice media scale, time out and fail independently.
- Voice connections get connection handling suitable for long-lived sessions; ordinary API timeouts do not apply to them.
- Edge TLS, WAF and rate limits apply to both paths, but with separate policies where needed.
- Two ingress paths mean two certificate/configuration surfaces to monitor and test.
- Voice provider and transport selection remain open; this decision only separates the entry paths.
- A voice ingress outage must not take down the API, and vice versa.
