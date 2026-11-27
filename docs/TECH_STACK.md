# Tech Stack

Python 3.10+ and Django 5.2 LTS support the available runtime. DRF supplies APIs; Requests supplies HTTP; Celery/Redis supply queues. PostgreSQL is production storage, SQLite is local development storage. pytest/pytest-django and Ruff verify code.

# Google authentication

`google-auth` provides scoped OAuth 2.0 service-account credentials for the
Search Console URL Inspection API. The app uses Requests for the fixed Google
endpoint and keeps the JSON key outside the repository.
