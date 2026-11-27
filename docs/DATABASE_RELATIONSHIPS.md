# Database Relationships

Implemented relationships: User owns Project and Location. Project protects its
Keyword rows; Keyword and Location are protected by KeywordLocation. Project,
Keyword and Location are archived with `is_active` rather than deleted through
user workflows. KeywordLocation validation requires the project's owner to equal
the location owner. Country is a shared protected catalog. RankCheck protects
its configuration and optional RankJob; RankingResult protects RankCheck.
CompetitorResult protects RankCheck and Competitor. Report protects its owner
and project and retains a JSON snapshot. ProviderConfiguration is a global
administrator-managed record without credentials.

Project.default_location optionally points to a Location owned by the same
user. KeywordLocation.source distinguishes project-generated configurations
from manual assignments so a default-location change can archive only the
generated rows without deleting historical checks.

Project has at most one SearchConsoleGrant; User may have multiple standalone
property grants. A grant belongs to exactly one project or user and is created
through superuser-only admin. IndexBatch belongs to User, optionally belongs
to Project, snapshots its check method and approved Search Console property,
and optionally references a Location for Serper checks. APIUsage also has an optional
Project for standalone URL checks. IndexCheck protects its batch and stores per-URL status,
inspection details and check time. Existing batches remain immutable history
when a grant changes or is deactivated.
