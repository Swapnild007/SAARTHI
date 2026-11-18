# Performance and reliability

| Measurement or fault | Observed evidence |
| --- | --- |
| Historical 33.49 s planning request | RCA replay measurement. Historical stage attribution remains unknown. |
| End-to-end deadline | 27 s from server middleware entry. Up to 3 s for bounded request-body intake. Cloud reservation and history read have 2.5 s ceilings, charged against the same clock. Approximately 3 s is reserved for terminal persistence and exit. The browser allows 32 s to receive and decode the result. |
| Provider attempts | At most two default routes per turn, each capped at 7 s in the worker. Worker subprocess bounds total engine execution and is killed and reaped at cutoff. Provider execution beyond a disconnected connection is outside SAARTHI's control. |
| Timeout and disconnect | API fixtures verify terminal failure or cancellation. The browser sends an authenticated, durable cancellation request because a client-side abort can leave the upstream connection open. A real sleeping subprocess was killed and reaped after an injected 0.1 s worker budget. |
| Rate limiting, outage and provider fallback | Test provider raises a 429, outage or timeout and checks stable error types. The successful second-route test records both provider attempt timings. No live latency percentile or provider SLO has been measured. |
| Duplicate prevention and recovery | Same turn ID replays the terminal result. Duplicate in-flight submissions are guarded in the browser. Database SQL verifies a competing reservation cannot start on the same active thread and verifies a stale reservation can become interrupted. |
| Detailed diagnostics | Completed workers return routing, engine, attachment and provider timing when those stages ran. Server logs include intake/reservation, history read and persistence. A killed worker cannot report its final in-process timings. |
| Long-running work | Turns exceeding the supported deadline fail with a terminal result. There is no background queue promising eventual completion. |

The Vercel recovery preview reported Python 3.12.16. Local tests used Python 3.12.14. Private staging still needs latency measurements across standard and specialist turns, provider failover under real conditions, and a gateway restart test for Hermes.
