# Scheduling

RankJob queues a project's eligible configurations after a request estimate and
confirmation. Pending jobs can be cancelled; workers update progress. The
confirmation request immediately asks Celery to dispatch the batch. If Redis
is unavailable, the job remains PENDING and the page shows a warning and a
local command to process the already confirmed checks. A second active job for
the same project is rejected to prevent duplicate paid requests.
The local command waits two seconds between requests by default; `--delay`
can be adjusted for the provider's current rate allowance.

TrackingSchedule stores daily, three-day, weekly and monthly frequencies,
and beat dispatches due schedules. Calendar-month advancement is implemented.
The schedule UI is available per project. It computes the next run in the
project's IANA time zone; beat advances monthly schedules by calendar month.
Broker integration, rate limits and concurrency behavior still require
PostgreSQL/Redis testing before production deployment.
