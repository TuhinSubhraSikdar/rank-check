# Security Guide

CSRF protection, Django password validation, owner-scoped querysets, escaped
templates and environment secrets are required. Public registration is disabled.
Only active superusers may access Django admin and create user accounts there;
ordinary users retain access only to their own projects and settings. Production
enforces HTTPS cookies and secure settings. No user-supplied URL is fetched.
