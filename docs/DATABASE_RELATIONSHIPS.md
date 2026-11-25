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
