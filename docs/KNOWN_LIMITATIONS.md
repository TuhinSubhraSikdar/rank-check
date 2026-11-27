# Known Limitations

The repository is under construction. Top 50/100 and device-specific ranking
remain disabled pending provider verification. Advanced analytics,
report date ranges, richer competitor comparisons and production integration are not yet
complete. No live credentials, PostgreSQL service or Redis broker were supplied.
Docker files have not been smoke-tested. HTTPS termination must be configured
before using production settings through the provided HTTP-only Nginx sample.
The local Docker command was blocked by snap runtime write restrictions in the
workspace sandbox; Docker Compose itself is installed but containers were not
started. Earlier confirmed rank jobs made live Serper requests; the new quick
URL search flow has only mocked transport verification.
Celery rate limiting is per worker. Avoid scaling beyond the provided single
worker topology until shared Redis throttling and PostgreSQL quota concurrency
checks are complete.
Search Console URL Inspection is implemented with a service account but has not
been exercised against a real verified property here. It reports Google's
indexed version only, not a live test or indexing request. The local per-property
daily quota guard does not account for calls made outside this application.
