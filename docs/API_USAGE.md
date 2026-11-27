# Api Usage

APIUsage records each provider request UUID, tenant, project, provider, status,
HTTP status, requested results, actual contiguous coverage and duration. Secrets,
query text and provider bodies are excluded. The ranking engine writes usage in
the same completion transaction as its attempt/result. The owner-only usage page
lists total requests, requests by project and recent attempts. Queue admission
checks a user's monthly Serper request quota against recorded and pending
Serper requests.
Concurrent quota reservation and provider-credit estimation still need
PostgreSQL-backed integration validation.
Serper URL index batches use the same monthly quota, counting pending rank and
Serper URL checks as well as recorded Serper requests. Each unique URL is one
confirmed paid Serper request; the usage row omits query text and the URL.
Google Search Console URL Inspection rows use provider
`google_search_console` and do not count toward the Serper quota. The app also
reserves a best-effort daily inspection allowance per approved property.
Standalone checks retain the account owner and have no project on their usage
row; the usage page labels them **No project**.
ProviderConfiguration exposes non-secret administrative settings. Celery limits
the rank-check task to `RANK_RATE_LIMIT` per worker (default 30/minute). The
provided Compose topology runs one worker with concurrency 1. A shared Redis
rate limiter is still required before scaling to multiple workers; the admin
configuration value does not yet change the task rate at runtime.

On 2026-11-25, five locally confirmed checks were processed against Serper and
five usage rows were recorded. No API key or provider body was stored.
