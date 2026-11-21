# Bulk and refresh validation, November 20

The downloader records received bytes across attempts, the last transfer timestamp, elapsed time and the failure stage for each archive in `run-report.json`. After 180 seconds, a transfer with a known length can continue if its measured rate predicts completion inside 25% of the original remaining budget, capped at 12 minutes. The extension also preserves 90 seconds for final work. Unknown-length or infeasible transfers keep the shorter deadline.

While the registry downloads are active, the runner checks robots rules for registry-declared website origins. Subsequent website checks reuse the policy cache. Ownership decisions still run after roles, workplaces and group evidence are available. Each registry family keeps its existing bounded fallback.

The entity-update cursor is optional on live refresh and is keyed by the exact batch chunk. It reloads complete, hashed source pages from the preceding validated run. A repeated inclusive event ID emits one event. Missing or corrupted pages trigger a fresh dated lookup; interrupted chunks cannot stage a new cursor. Cutoff runs, roles and workplaces use their existing lookup paths.

## Checks

- Offline regressions cover a slow but nearly complete download, read timeouts, truncated gzip, and one incomplete archive alongside a complete empty archive.
- With identical synthetic HTML and a 12-request cap, breadth-first discovery found the one supported website. Legacy discovery found none. Both rejected the unrelated pages. This fixture measures scheduling behavior only.
- Cursor regressions cover cold start, inclusive boundary deduplication, interrupted refresh, retained source identity and recovery from a damaged artifact.

## Measured results

All 350 Python tests and 18 frontend tests passed. A live cursor probe restored 660 historical events for the 99 resolved companies in the development smoke run and refreshed the two registry feeds in two requests without errors.

The [cold-start smoke report](bulk-smoke-100-20261120.json) matches the scale report's code digest. It returned 100 valid envelopes in 326 seconds using 654 requests, two workers and $0 paid API spend. Its snapshot audit passed.

| Same 1,100 inputs | Previous build, legacy scheduling | Upgraded bulk, breadth scheduling |
|---|---:|---:|
| Valid envelopes | 1,100 | 1,100 |
| Leadership available | 93 | 1,096 |
| Workplaces available | 75 | 837 |
| Completed website checks, companies | 65 | 118 |
| Websites published | 16 | 25 |
| Companies with social profiles | 5 | 7 |
| Company news / jobs | 0 / 0 | 0 / 0 |
| Outbound requests | 1,920 | 1,919 |
| Seconds | 560.1 | 491.0 |
| External API spend | $0 | $0 |

An intermediate legacy run received 43.6 MB of roles and 42.1 MB of workplaces before both timed out. Two separate development HEAD requests reported archive sizes of 130.0 MB and 61.9 MB. In the upgraded run, roles used the measured-rate extension and completed download plus parsing in 248.5 seconds. Workplaces finished in 110.2 seconds. Each archive took one request. Live transfer rates varied, and scheduling changed between the two table columns.

The [scale report](bulk-scale-1100-20261120.json) records the final build and budgets. A separate direct-API parity check matched all 60 company/family comparisons across 30 sampled companies, including companies with and without registered workplaces. Its 60 requests are outside the measured run. The retained-evidence audit passed, including 48,658 account claims.

Of the 25 website matches, 20 retained organisation-number evidence and five relied on the legal name. Four of those five sites could be reopened for name review; the independent fetch of Globalen failed. These observations do not establish population precision. The run left 976 resolved companies without a website attempt. Keep breadth selectable pending broader attribution review, and treat news and jobs as outstanding coverage gaps.
