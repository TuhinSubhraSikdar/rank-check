# RankTracker agent instructions

Read this file before modifying this repository. RankTracker is a multi-tenant
Django SEO application. Correct rankings, tenant isolation, preserved history,
and honest provider limitations take precedence over feature count.

## Stack and structure
Python 3.10+, Django 5.2 LTS, DRF, PostgreSQL (SQLite for local use), Celery,
Redis, Requests, Django templates, custom CSS, Chart.js, pytest and Ruff.
`config/` owns settings and URLs; `apps/<domain>/` owns domain models, forms,
services, selectors and views; `templates/`, `static/`, `tests/`, `docs/`, and
`deploy/` contain shared presentation, verification, documentation and operations.
See docs/ARCHITECTURE.md and IMPLEMENTATION_PLAN.md before planning work.

## Conventions
- PEP 8; snake_case functions/modules, PascalCase classes, descriptive names.
- Validate inputs in forms/serializers and services. Views orchestrate only.
- Every tenant service takes an actor and checks ownership. Scope querysets
  before looking up IDs. Staff privileges do not implicitly bypass tenant APIs.
- Public signup is disabled. Only active superusers access Django admin and
  create additional accounts. Do not reintroduce public registration casually.
- Project.default_location creates automatic tracking configurations for all
  active keywords; manual configurations remain separate and history is kept.
- Use the ORM, transactions for related writes, database constraints for
  uniqueness, indexes for tenant/history queries, and UTC-aware timestamps.
- Archive projects and keywords. Historical records use protective relations;
  normal workflows never mutate or delete observations.
- Separate billable attempts, normalized observations and queued work.
- Never store secrets in code, logs, request metadata, reports or browser code.
- No outbound fetching of user URLs. Escape HTML and neutralize CSV formulas.
- No network or billable API calls in tests; mock the provider transport.
- Add regression tests for security, provider semantics and business logic.
- Update feature documentation, CHANGELOG.md and IMPLEMENTATION_PLAN.md with
  changes. Document unfinished features as planned, never as implemented.

## Extending the system
New apps: create `apps/<name>/`, AppConfig with full dotted name, register in
settings, add scoped URLs/services, tests and architecture documentation.
New models: explain ownership and deletion policy, add constraints/indexes,
then `.venv/bin/python manage.py makemigrations` and `migrate`. Commit migrations.
New providers: implement BaseSERPProvider and explicit capability metadata;
verify official documentation, normalize results, redact secrets, add fixtures
and transport/error tests. Do not infer pagination, depth or device support.
Ranking changes: inspect docs/RANKING_ENGINE.md, preserve explicit positions,
coverage and statuses; test domain boundaries, duplicates, sparse results,
movement, failed attempts and history before editing aggregation/report logic.

## Verification
Use `.venv/bin/pytest`, `.venv/bin/ruff check .`,
`.venv/bin/python manage.py check`, and
`.venv/bin/python manage.py makemigrations --check --dry-run`.
Production needs PostgreSQL/Redis integration checks and `check --deploy` with
real deployment environment settings. Never claim those passed from SQLite.
