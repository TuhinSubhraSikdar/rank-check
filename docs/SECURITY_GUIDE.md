# Security Guide

CSRF protection, Django password validation, owner-scoped querysets, escaped
templates and environment secrets are required. Public registration is disabled.
Only active superusers may access Django admin and create user accounts there;
ordinary users retain access only to their own projects and settings. Production
enforces HTTPS cookies and secure settings. No user-supplied URL is fetched.
Search Console calls go only to Google's fixed URL Inspection endpoint. A
superuser grants a property to one project or account in admin; project checks
must match the owner project and approved property, while standalone checks
must match the approved account property. Standalone Serper checks may use an
owned location or the fixed US/English request settings. They send public
search queries without fetching the submitted URL. The read-only service account JSON
stays outside Git and is mounted read-only in containers. Tokens and raw Google
error responses are not stored or shown to users.
Workers recheck grant or location access before dispatching a queued URL check.
Revoked grants and archived locations cancel pending attempts without an API
request. Existing attempt history is retained.
