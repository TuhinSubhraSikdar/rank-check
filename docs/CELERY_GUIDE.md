# Celery Guide

Confirmation requests immediate dispatch. Celery beat also periodically
dispatches pending checks to a worker, which records attempts and usage. A
check stays PENDING until a dispatcher and worker run. If the broker cannot be
reached, confirmation displays a warning and leaves the checks pending.

For local development without Redis, `run_pending_checks` processes only
already confirmed pending checks. It sends real billable requests. The command
defaults to 25 checks and a two-second delay between requests. Use
`--project ID`, `--limit N`, or `--delay SECONDS` when needed. Cancellation
applies before each pending check is claimed. Worker concurrency and rate are
bounded by deployment configuration; ambiguous billable failures are not
retried automatically.
