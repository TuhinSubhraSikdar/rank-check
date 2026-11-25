# Changelog

## 0.1.0 — 2026-11-24 (in development)

- Established architecture, phased roadmap and documentation.
- Added Django foundation, custom user, authentication and responsive layout.
- Added tenant-scoped project CRUD and archive workflow with normalized domains.
- Added keyword CRUD, atomic bounded CSV import and formula-safe CSV export.
- Added country/location management and unique owner-validated tracking configurations.
- Added a capability-gated Serper adapter, immutable rank attempts/results,
  safe domain matching, movement calculation and per-request API usage records.
- Added queued rank jobs, basic history and dashboard, private snapshot reports,
  Celery dispatch tasks and initial container deployment files.
- Added competitor extraction from existing organic results and schedule settings.
- Added owner-only API usage page and project navigation for jobs, reports and competitors.
- Added non-secret provider configuration and constrained tracking forms to verified capabilities.
- Added history date/status filters, a report location summary and Celery task rate limits.
- Added a repeatable starter country catalog so new installations have choices in the Location form.
- Added a local command for confirmed pending checks and clarified worker requirements in the job UI.
- Disabled public signup, restricted admin to superusers, added project-wide location assignment and per-user dark theme.
- Added Docker build exclusions and Git upload guidance.
- Dispatch confirmed jobs to Celery immediately, warn when the broker is unavailable,
  reject duplicate active project jobs, and pace local pending-check processing.
- Added the author's GitHub and LinkedIn links to the shared application footer.
