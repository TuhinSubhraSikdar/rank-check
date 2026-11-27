# Serper Api Integration

Verification on 2026-11-24: the supplied `/api-reference` URL returns HTTP 404.
Serper's official public playground bundle constructs POST requests to
`https://google.serper.dev/search` with `X-API-KEY` and JSON fields `q`,
`location`, `gl`, `hl`, `num`, and `page`. Its Search result selector exposes
only `num=10`; the homepage response example includes `organic` entries with
explicit `position`, `title`, `link`, and `snippet`.

The implemented adapter sends a single Top 10 request, normalizes only the
organic array, preserves provider positions, measures contiguous coverage, and
returns explicit timeout, API error, invalid response, or incomplete states.
Top 50/100 execution is rejected because absolute position semantics across
pages have not been verified. Desktop/mobile execution is rejected because the
playground exposes no Search device parameter. Tests mock HTTP and consume no
credits. Metadata includes endpoint, page, duration and response status, never
the API key or provider response body.

Quick URL checks use the same Search endpoint with `q=site:<URL>`, `gl=us`,
`hl=en`, and `num=10`, omitting the city-level `location` field. The returned
organic links are compared with the submitted URL. An absent exact match is
reported only as **Not found in search**, because a `site:` query is not an
exhaustive index inventory. This unlocated request is covered by mocked tests;
no paid provider call was made for this change.
