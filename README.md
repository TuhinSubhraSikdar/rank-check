# RankTracker

A multi-user Django application for geographical Google organic rank tracking,
historical comparisons and client reports. This repository is being built in
tested phases; consult [the implementation plan](IMPLEMENTATION_PLAN.md) for
current status and [the documentation index](docs/README.md) for details.

## Architecture
Django 5.2 LTS and DRF, PostgreSQL (optional SQLite), Celery/Redis, Requests,
Django templates and custom responsive CSS. The provider adapter isolates
Serper semantics from ranking calculations and UI code. Projects define tenant
ownership; immutable observations preserve historical results.

## Development
Python 3.10+ is required. Run from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_countries
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

For local SQLite, keep `DATABASE_ENGINE=sqlite` in `.env`. Set a persistent
`DJANGO_SECRET_KEY` before relying on sessions or password reset links. The
development settings print reset emails to the console. Production requires an
SMTP server. The seed command adds a starter country catalog without changing
existing countries. Create the first superuser with the command above, then
sign in. Public registration is disabled. Only superusers can open Django admin
and create additional users there. Create a project, add a location and select
that project in the location form to assign all its existing and future keywords
to the location. You can also select or change the project location on the
project's Edit page. Manual keyword locations remain available. The keyword
import page supplies a sample UTF-8 CSV. A project's
Run check page displays the exact estimated request count and requires an
explicit POST before queuing paid work. Only provider-default Top 10 checks are
enabled until deeper positions and device targeting are verified.

For manual and scheduled checks, run Redis plus a Celery worker and beat in
separate terminals. Set `SERPER_API_KEY` in `.env` before dispatching jobs:

```bash
redis-server
.venv/bin/celery -A config worker --loglevel=INFO --concurrency=1
.venv/bin/celery -A config beat --loglevel=INFO
```

For lightweight local use without Redis, previously confirmed checks can be
processed from a terminal outside the HTTP request:

```bash
.venv/bin/python manage.py run_pending_checks --limit 25
```

This sends real Serper requests and consumes provider credits. It only handles
checks already confirmed in the project UI. Use `--project ID` to limit one
project. The command spaces requests two seconds apart by default. If Redis is
unavailable when you confirm a job, the job page warns you and retains the
checks as PENDING until a worker or this command runs. Celery/Redis remains the
deployment path for scheduled and bulk work.

The dashboard shows latest observations. Ranking history lists check attempts;
Reports creates owner-only, standalone HTML and UTF-8 CSV snapshots. Schedules
can be configured per project. The API key is never sent to the browser. The
light/dark appearance setting is under **Settings** and is saved per user.

**URL index checks** accepts up to 25 URLs per batch, with or without a project.
For the simplest flow, open **URL index checks → Quick URL search check** and paste
URLs. It sends Serper `site:` searches using US/English settings without a
project or location. The report says **Found in search** or **Not found in
search**; absence does not prove non-indexing. The advanced form still lets
you choose a project or an optional owned location for Serper. Selecting a
project uses its default location and limits URLs to its domain.
Google Search Console checks need an administrator-approved property for your
account (standalone) or project. They show Google's reported indexed-version
status, coverage, canonical and last crawl information. Follow
[the setup guide](docs/SEARCH_CONSOLE_INDEXING.md). Serper site search checks
whether an exact URL appears in `site:` results and uses one paid request per
URL. If Redis/Celery is unavailable, process a confirmed batch with
`.venv/bin/python manage.py run_pending_index_checks --batch ID`.

Run local verification with:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

For PostgreSQL, set `DATABASE_ENGINE=postgresql` and `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`.
Apply migrations against that database before starting the web process.

Docker Compose defines PostgreSQL, Redis, Gunicorn, worker, beat and Nginx.
Set a 50-character or longer `DJANGO_SECRET_KEY`, database password, allowed
hosts, trusted origins, SMTP values and Serper key in `.env`. Then run:

```bash
docker compose build
docker compose up -d db redis
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_countries
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
```

The supplied Nginx sample listens on HTTP port 8080 and assumes a trusted HTTPS
terminator sits in front of it. Production settings enforce HTTPS and secure
cookies; configure the terminator and forwarded protocol before using the app.
Do not expose PostgreSQL or Redis publicly. Take database backups and verify
restore procedures before upgrades. Container and PostgreSQL/Redis integration
checks have not been run in this workspace.

## Git upload

The local `.env`, SQLite database, virtual environment, logs, media and generated
static files are ignored by Git. `.dockerignore` excludes them from Docker builds.
Upload source files, migrations, templates, static assets, docs, `.env.example`,
requirements and deployment files. Set production secrets in your host's
environment; never add `.env` to Git. This directory currently sits inside a
parent Git worktree, so inspect the repository root before staging or pushing.

## Provider verification
Serper's public homepage is accessible; `/api-reference` was unavailable to the
documentation reader on 2026-11-24. Pagination, maximum depth and device support
remain verification gates. RankTracker will not advertise unsupported results.

## Screenshots
Screenshots have not yet been captured. No demonstration rankings are included
in the production database.

## Project guides
- [Architecture](docs/ARCHITECTURE.md)
- [Agent instructions](AGENTS.md)
- [Implementation plan](IMPLEMENTATION_PLAN.md)
- [Roadmap](docs/ROADMAP.md)

## Current limitations
Top 50/100 execution and mobile/desktop measurement remain disabled pending
Serper capability verification. Historical charts, advanced analytics, client
branding logos, report date comparisons and public report sharing are planned.
See the implementation plan for exact phase status.
