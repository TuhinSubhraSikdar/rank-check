# Deployment

The repository includes a Dockerfile, Compose services for PostgreSQL, Redis,
Gunicorn, one Celery worker, one beat process and Nginx, plus a sample Nginx
reverse proxy configuration. Supply `.env`, a 50-character Django secret,
database password, SMTP and Serper credentials, then follow README.md.
Nginx currently listens on HTTP only; deploy a trusted HTTPS terminator in
front and set allowed hosts/trusted origins accordingly. Run migrations before
starting web and take a PostgreSQL backup before upgrading. Do not expose
database or Redis ports. Container and PostgreSQL/Redis integration checks have
not been completed in this workspace.
For Google Search Console, place the service account JSON in `.secrets/`, set
`GSC_SERVICE_ACCOUNT_FILE=/run/gsc/service-account.json`, grant the service
account access to the verified property in Search Console, and create the
project's SearchConsoleGrant in superuser-only admin. Compose mounts the key
directory read-only into web and worker; `.secrets/` is excluded from Git and
Docker build context.
