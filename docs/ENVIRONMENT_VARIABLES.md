# Environment Variables

Planned environment: DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, database credentials, REDIS_URL, SERPER_API_KEY, SERPER_BASE_URL and SMTP settings. Never commit an actual .env file.

`GSC_SERVICE_ACCOUNT_FILE` is an optional path to a deployment-owned Google
service account JSON key; leave empty to disable Search Console checks. Keep
the file in `.secrets/` locally or mount it at `/run/gsc/` in Compose. Never
commit the key. `GSC_TIMEOUT` defaults to 20 seconds and
`GSC_DAILY_PROPERTY_LIMIT` defaults to 2,000 checks per UTC day per property.
