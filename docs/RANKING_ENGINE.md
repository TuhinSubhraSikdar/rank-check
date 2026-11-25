# Ranking Engine

Implemented core engine creates a RankCheck attempt before provider execution,
then records one immutable RankingResult only when an organic observation is
meaningful. API/transport failures remain on the attempt and do not create or
replace a ranking result. Every dispatched provider response creates an APIUsage
row keyed by its request UUID.

Domain matching parses the result URL hostname. Exact matching is always
supported; optional subdomain matching uses a dot boundary, so
`example.com.fake.test` never matches `example.com`. Multiple matches select the
lowest explicit provider position. Movement equals previous ranked position minus
current position. A previous missing result followed by a position is marked
newly ranked. Complete coverage with no match becomes NOT_FOUND; incomplete
coverage remains INCOMPLETE with no invented position. Queue dispatch, bulk
confirmation and basic history UI are now implemented. Advanced history filters
and retry controls remain Phase 5 work.

For local installations without Redis, `manage.py run_pending_checks` processes
only previously confirmed pending jobs from a separate terminal. It sends real
Serper requests and records usage. The supplied production path still uses
Celery/Redis. If Serper returns nine organic results for a Top 10 request, the
check remains INCOMPLETE, and absence is not reported as NOT_FOUND.
