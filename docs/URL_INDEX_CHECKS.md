# Quick URL search checks

Open **URL index checks → Quick URL search check**, paste up to 25 HTTP(S) URLs, and
confirm. No project, saved location, or Search Console connection is needed.
Each unique cleaned URL queues one Serper Google Search request with
`q=site:<URL>`, `gl=us`, `hl=en`, and `num=10`; no city-level `location` is
sent. The app compares the returned organic links against each exact cleaned
URL and keeps the result in an owner-only batch report. It never fetches the
submitted page directly.

The report uses **Found in search** when the exact URL appears and **Not found
in search** when it does not appear in the returned results. The second outcome
does **not** prove that the URL is absent from Google's index; [Google says a
`site:` search may omit indexed URLs](https://developers.google.com/search/docs/monitor-debug/search-operators/all-search-site).
Provider errors
and timeouts are shown separately. For Google's reported indexed-version
status, use the separate [Search Console inspection](SEARCH_CONSOLE_INDEXING.md)
with an approved property.

Serper checks consume one provider request per unique URL and count toward the
user's monthly Serper quota. Confirmation queues work for Celery. If no worker
is available, the report shows a local command that processes only the already
confirmed batch. Existing project-based checks still use the project's default
location; the advanced form also permits an optional owned location for a
standalone Serper check.

The request uses Serper's documented Search fields for query, country,
language, and result count. The unlocated request and exact-match behavior are
covered by mocked transport tests; no new paid provider request was made to
verify this change. [Serper public Search example](https://serper.dev/).
