# Database Schema

Planned models: custom User and Profile; Project; Keyword; Country and Location; KeywordLocation; RankJob, RankCheck and RankingResult; Competitor and CompetitorResult; TrackingSchedule; Report; APIUsage; ProviderConfiguration. Actual migration details will be recorded as phases land.

Migration `ranktracker.0006` adds SearchConsoleGrant (one approved property per
project), IndexBatch.method and site_url snapshot, and optional location for
Search Console batches. IndexCheck stores the returned verdict, coverage state,
Google canonical URL and last crawl time. Older Serper batches retain their
default `SERPER` method and existing history.

Migration `ranktracker.0007` permits an IndexBatch without a project and adds
an optional account owner to SearchConsoleGrant. A database check constraint
requires exactly one grant scope: project or account. Migration `usage.0002`
allows APIUsage.project to be null for standalone checks. Historical batches,
attempts and usage rows are preserved.
