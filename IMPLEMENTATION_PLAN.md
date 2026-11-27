# Implementation plan

Status vocabulary: NOT STARTED / IN PROGRESS / COMPLETED / BLOCKED.
Each phase depends on the preceding foundation; provider capability gates can
remain BLOCKED without inventing support. Tests use mocked HTTP only.

| Phase | Tasks | Status | Testing | Documentation |
|---|---|---|---|---|
| 0 Inspection and planning | Inspect workspace; architecture; ownership and ER design; folder structure; agent rules; documentation index; decisions; dependencies | COMPLETED | Empty workspace inspected | Architecture, agent guide and documentation index written |
| 1 Foundation | Settings; custom user migration; profile; login/logout/reset/change; superuser-only admin and private user creation; secure layout; health | COMPLETED | Authentication, private signup and admin permission tests pass | Foundation documented |
| 2 Projects and keywords | Owned project CRUD/archive; domain normalization; keyword CRUD/archive; bounded atomic CSV import/export; filters | COMPLETED | CRUD, isolation, CSV atomicity and formula-injection tests pass | Keyword workflow documented |
| 3 Locations | Country catalog; owned locations; project-wide default location; unique keyword/location/device configuration | COMPLETED | Isolation, project-wide assignment, switching and seed tests pass | Starter catalog and project location setup documented |
| 4 Provider | Verify official parameters; adapter; strict normalization; errors/timeouts; usage; capability gates | COMPLETED | Mocked requests, normalization, timeout, error and capability tests pass | Verified playground behavior and limits documented; non-secret admin configuration added |
| 5 Ranking engine | Queue jobs; immutable attempts/results; coverage; matching; movement; bulk estimate/confirmation; history | IN PROGRESS | Queue ownership/quota/cancel and local dispatcher tests pass | Job UI and project/status/date history filters added; retry pending |
| 6 Analytics | Latest valid result selectors; real metrics; searchable ranking table; history and comparison charts | IN PROGRESS | Existing ranking tests pass; analytics tests pending | Basic dashboard metrics added; charts and advanced filtering pending |
| 7 Reporting | Scoped streaming CSV; immutable report snapshots; standalone HTML; branding; private history/download | IN PROGRESS | Private report access test passes | Snapshot reports with location summary added; date filtering and historical comparison pending |
| 8 Automation | Celery/Redis; project schedules/time zones; progress/cancel/retry; quotas; bounded batch dispatch | IN PROGRESS | Queue, schedule ownership and unavailable-broker regression tests pass; broker integration untested | Worker/beat and schedule UI added; immediate dispatch on confirmation; local dispatcher paced; robust rate limiting pending |
| 9 Competitors | Owned competitor CRUD; extraction from same response; position and overlap views | IN PROGRESS | Same-response extraction and ownership test passes | CRUD and observations added; overlap/comparison views pending |
| 10 Production readiness | Security review; tests/lint/migrations; Docker/Gunicorn/Nginx; operations and documentation audit | IN PROGRESS | SQLite tests pass; Docker/PG/Redis integration pending | Container files added; TLS and backup operations pending |
| URL index checks | Paste, clean, sort and deduplicate project URLs; queue one paid `site:` query per unique URL; report exact matches and inconclusive outcomes | COMPLETED | Mocked provider, tenant, quota and URL matching tests pass; live provider behavior unverified | UI and limitations documented |
| Search Console inspection | Admin-approved project property; service-account authentication; owner-scoped URL Inspection batches; indexed-version verdicts and history | IN PROGRESS | Mocked Google transport, property boundary, quota, tenancy and reporting tests pass; live property check pending | Setup, security and API limitations documented |
| Standalone URL checks | Optional project on URL batches and usage; owned Serper location or account-approved Search Console property; scoped reports | COMPLETED | Mocked standalone provider and tenant tests pass; live providers unverified | Form, setup and ownership documentation updated |
| Quick URL search check | URL-only Serper `site:` queue; US/English search defaults; exact-match report wording; owner quota and history | COMPLETED | Mocked unlocated request, timeout, queue and private report tests pass; live request unverified | Quick check guide and Serper semantics updated |

## Provider verification gates
- Verify request endpoint, authentication, country, language and location syntax.
- Verify maximum depth and pagination semantics before enabling Top 50/100.
- Verify device targeting before offering desktop/mobile as measured results.
- If evidence is unavailable, expose provider-default device and conservative
  first-page coverage; clearly mark deeper/device-specific tracking blocked.

## Validation log
- 2026-11-24: workspace contains only empty managed metadata directories.
  Python 3.10.12 is available as `python3`; there is no pre-existing application.
- 2026-11-24: phases 1–3 verified with 12 SQLite tests. PostgreSQL concurrency
  remains a production integration check.
- 2026-11-24: provider adapter and core ranking engine verified with 19 tests.
  No live or billable Serper request was made.
- 2026-11-25: 23 SQLite tests pass. Competitor observations and schedule UI
  added. Production services and billable provider calls remain untested.
- 2026-11-25: after API usage UI, form capability guards and provider settings,
  23 SQLite tests, Ruff, Django checks and migration drift check pass.
- 2026-11-25: local dispatcher processed five previously confirmed Serper checks.
  Three checks returned ten contiguous results; two returned nine and were
  marked INCOMPLETE. Usage recorded five requests. Suite: 25 tests pass.
- 2026-11-25: public signup removed, admin restricted to superusers, sole local
  account promoted to superuser, project-wide location assignment and saved dark
  theme added. Production checks and Compose syntax validated with dummy secrets.
- 2026-11-25: shared footer updated with GitHub and LinkedIn profile links;
  verified with Django system checks and template rendering.
- 2026-11-26: owner-scoped URL index batches, worker/local processing and per-URL
  reports added. A missing `site:` result is reported as not confirmed, not as
  proof of non-indexing. SQLite unit tests and Django checks pass; no live
  provider request was made for this feature.
- 2026-11-27: Search Console URL Inspection added with admin-approved property
  grants and separate result semantics. Migration applied locally; 48 SQLite
  tests, Ruff, Django checks and migration drift check pass. No real Search
  Console credentials or verified property were available. Docker Compose
  validation remains blocked by the local Snap runtime restriction.
- 2026-11-27: standalone Serper and Search Console URL batches added with owner
  location/property selection, nullable project usage and revocation checks.
  Migrations applied locally; project history preserved. 52 SQLite tests,
  Ruff, Django checks and migration drift check pass. Live provider and
  PostgreSQL/Redis integration remain unverified.
- 2026-11-27: quick URL-only Serper flow added with US/English search targeting,
  no project or saved location, and exact-result reporting. 55 SQLite tests,
  Ruff, Django checks and migration drift check pass. No paid request was made
  for this flow.
