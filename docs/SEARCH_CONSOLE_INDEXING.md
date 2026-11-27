# Google Search Console URL Inspection

RankTracker offers two clearly labeled URL check methods. **Google Search
Console** calls Google's read-only URL Inspection API and reports the indexed
version's verdict, coverage detail, Google-selected canonical, and last crawl
time when supplied. **Serper site search** looks for an exact URL in organic
`site:` results; an absent result is only `NOT_CONFIRMED`.

## Administrator setup

1. Enable the Search Console API in a Google Cloud project and create a service
   account. Download its JSON key to a protected location outside Git. The
   application requests only the `webmasters.readonly` OAuth scope.
2. In Google Search Console, add that service account email as a user of the
   intended verified property. Use the exact property name Google shows:
   `sc-domain:example.com` or a URL prefix such as `https://www.example.com/`.
3. Set `GSC_SERVICE_ACCOUNT_FILE` in `.env` to the credential file path. For
   local use, `.secrets/service-account.json` works. This directory is ignored
   by Git. For the included Compose setup, put the key at
   `.secrets/service-account.json` and set
   `GSC_SERVICE_ACCOUNT_FILE=/run/gsc/service-account.json`; Compose mounts the
   directory read-only into the web and worker containers.
4. Apply migrations. In Django admin, create a **Search Console Grant** for
   each allowed project or account. Choose exactly one Project or Owner on each
   grant. Only a superuser can create or change grants. Project grants must
   cover the project domain; account grants allow standalone checks for URLs
   within that property. Standard users cannot select another user's grant or
   read another user's reports.
   Deactivating a grant stops its pending checks before the worker calls Google;
   earlier report history remains available to its owner.
5. Start Redis, Celery worker and beat for automatic dispatch, or use the
   local command shown in a pending batch report.

## User workflow

Open **URL index checks → Paste URLs**, choose **Google Search Console**, then
select either an approved project or **No project** plus an approved account
property. Paste up to 25 URLs. The form cleans and deduplicates URLs.
Confirmation creates an owner-only historical batch. The result page
shows `INDEXED` for Google's `PASS` verdict, `NOT_INDEXED` for `NEUTRAL` or
`FAIL`, and `UNKNOWN` for an unspecified verdict. `ACCESS_ERROR`,
`RATE_LIMITED`, `TIMEOUT`, `API_ERROR`, and `INVALID_RESPONSE` are inconclusive.
The original Google verdict and coverage text remain visible for context.

The API inspects Google's indexed version; it does not test the current live
page and cannot request indexing. Google's property and API quotas apply. The
app enforces a configurable best-effort UTC daily limit per property
(`GSC_DAILY_PROPERTY_LIMIT`, default 2,000), but other clients using the same
Google property may consume quota outside the app. Search Console calls are
recorded in API usage and do not consume the app's Serper request quota.

No live Google credentials are included in the repository. Automated tests
mock both credential refresh and HTTP transport; a real property connection
must be verified after deployment.

Official references: [URL Inspection request and response](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect),
[index status fields](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult),
[authorization](https://developers.google.com/webmaster-tools/v1/how-tos/authorizing),
and [usage limits](https://developers.google.com/webmaster-tools/limits).
