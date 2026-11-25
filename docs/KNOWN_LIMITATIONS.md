# Known Limitations

The repository is under construction. Top 50/100 and device-specific ranking
remain disabled pending provider verification. Advanced analytics,
report date ranges, richer competitor comparisons and production integration are not yet
complete. No live credentials, PostgreSQL service or Redis broker were supplied.
Docker files have not been smoke-tested. HTTPS termination must be configured
before using production settings through the provided HTTP-only Nginx sample.
The local Docker command was blocked by snap runtime write restrictions in the
workspace sandbox; Docker Compose itself is installed but containers were not
started. No live Serper request was issued.
Celery rate limiting is per worker. Avoid scaling beyond the provided single
worker topology until shared Redis throttling and PostgreSQL quota concurrency
checks are complete.
