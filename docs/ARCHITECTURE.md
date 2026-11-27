# Technical architecture

## Design
RankTracker is a modular Django monolith with a separately deployed Celery
worker and beat scheduler. PostgreSQL is the production system of record;
SQLite is supported for single-process development and unit tests. Redis is
the broker and production cache. Templates serve the UI, DRF serves scoped
read APIs, and domain services own validation and transactional writes.

## Application boundaries
| App | Responsibility |
|---|---|
| accounts | Custom user, profile, authentication and preferences |
| projects | Tenant-owned sites and matching policy |
| keywords | Normalized keyword uniqueness, import and archive |
| locations | Country catalog and tenant-owned geographical targeting |
| ranktracker | Tracking configurations, jobs, attempts, immutable observations and matching |
| ranktracker URL checks | Owner-scoped URL batches and attempts using Serper site search or Google Search Console URL Inspection; methods have distinct status meanings |
| serp_providers | Capability-aware provider adapters and normalization |
| dashboard | Scoped selectors, metrics and chart payloads |
| reports | Immutable report snapshots, safe CSV and standalone HTML |
| scheduling | Due schedules, queue dispatch and task lifecycle |
| competitors | Competitor definitions and observations from existing SERPs |
| usage | Billable request accounting and quotas |
| core | Shared validation, ownership helpers, time and security utilities |

## Request flow
An authenticated actor submits a validated form. A service scopes all IDs to
that actor, estimates requests and creates a job after confirmation. Workers
claim attempts transactionally, reserve quota, call a provider outside a
database transaction, then atomically persist observations and completion.
No view performs bulk external requests. Results are append-only. Failed
attempts remain visible without replacing the latest valid observation.

URL check batches belong directly to an account and may optionally retain a
project. Serper batches optionally retain a selected owned location; without
one, the quick flow uses US/English request settings. Each unique cleaned
URL has one attempt;
the batch and attempt rows are preserved as history. The worker queries
`site:<URL>` through Serper without fetching the submitted URL. A matching
organic URL is "found"; absence is "not confirmed" because `site:` results are
not an exhaustive index inventory. Provider errors are inconclusive.
Search Console batches use an administrator-approved property grant for one
project or account and a deployment-owned read-only service account. The grant and URL
scope are checked before queuing. Google credentials are never stored in the
database, sent to the browser or read from user input. Indexed-version verdicts
are kept separate from Serper search-result signals.

## Data integrity and tenancy
Project.owner is the tenant boundary. Keyword, configuration, jobs, history,
competitor and report ownership derive through project. Locations belong to
users; countries are a shared administrator-managed catalog. Cross-tenant
relationships are rejected by services/model validation. Protective foreign
keys and archive workflows preserve history. Database unique constraints
back case-normalized keyword and tracking-configuration uniqueness.

Public account registration is disabled. Superusers create accounts through a
restricted Django admin. Project.default_location is an optional owned Location
that generates configurations for all active project keywords. Those automatic
configurations are archived when the project changes its default, while manual
ones remain active.

## Provider semantics
Provider support is a capability contract, not a UI promise. Store requested
depth and actual contiguous organic coverage separately. Sparse or truncated
responses cannot prove absence at the requested depth. A found position may
be retained with its actual coverage. Unknown device targeting is represented
as provider-default, never relabeled desktop/mobile. No undocumented paging.

## Deployment
Nginx terminates/proxies HTTP and serves collected static assets. Gunicorn
serves Django. Dedicated worker and single beat processes share PostgreSQL
and Redis. Environment variables carry secrets; production fails closed if
required values are absent. SMTP handles resets. Backups, TLS and external
monitoring remain operator responsibilities.

## Planned folder structure
`config/settings/{base,development,production}.py`; `apps/<domain>/`;
`templates/{base,components,registration,...}/`; `static/{css,js,vendor}/`;
`tests/`; `docs/`; `deploy/`; `scripts/`; runtime `media/` and `logs/`.
The implementation plan records actual phase completion separately from this design.
