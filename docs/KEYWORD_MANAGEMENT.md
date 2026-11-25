# Keyword Management

Implemented: keywords are unique case-insensitively inside a project, normalize
internal whitespace, and archive without deleting history. All views scope the
project through the authenticated owner. Search, create, edit and archive views
are available per project.

CSV import accepts UTF-8/UTF-8-BOM files up to 2 MB and 5,000 data rows. The
`keyword` header is required; `target_url`, `tags` and `search_intent` are
optional. Empty, repeated and existing keywords are counted as skipped. Every
candidate row is validated before one atomic bulk insert, so invalid URLs or
intents leave the database unchanged. Export streams ORM rows in chunks and
prefixes cells beginning with spreadsheet formula characters with an apostrophe.
