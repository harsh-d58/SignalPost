# Model improvement programme

Updated 12 November 2026 after implementing and testing the follow-up fixes. This document is the active backlog. The earlier [batch diagnosis](batch-accuracy-diagnosis.md), [fix record](batch-accuracy-fix-plan.md) and [analysis](../../analysis.md) preserve historical results.

## Bulk website benchmark plan

The [deep website search plan](deep-website-search-plan.md) defines a proposed 1,500-company, up-to-3,000-candidate benchmark, independent ownership labels, random/positive/adversarial cohorts, and separate discovery/attribution/extraction tests. It is a plan; the new corpus and harness are not yet built.

## Latest release pass — 12 November

The latest [release report](../../reports/release-readiness-20261112.md) supersedes earlier open statuses for filing-history checks and verification/enrichment sequencing. The final suite passes **267 tests** on pinned Python 3.12. The fresh scale run returned 1,100 valid envelopes in 429.3 seconds with 1,920 requests; the direct smoke returned 100 valid envelopes in 220.1 seconds with 607 requests. Both cost $0 externally and passed source audits. The smoke's 928 filing-history claims now pass their source-specific checks.

Website verification now precedes optional detail enrichment. A final publisher-reference correction recovered three company articles in a focused live check and has negative/ambiguity/source-fragment tests. The larger runs preceded that correction; their totals are not a final-code coverage estimate. Remaining blockers are independent labels, approved job-source access, broader evidenced identity scopes, and connection-time DNS protection. The review export contains 189 unlabeled development tasks for a reviewer and never fabricates judgments.

## Current implementation status

This table supersedes the original diagnostic statuses below. All **255 tests pass**, including the original four failures, source mutation checks, closure/reopening tests and direct/bulk mock batches up to 1,100 companies. CI now runs the diagnostics and audits live smoke evidence.

| Item | Implemented and tested | Remaining work |
|---|---|---|
| R01 publisher conflict | A conflicting main-article publisher blocks all extraction routes, including HTML fallback. Explicitly unrelated embedded articles do not block the main article. | Independent mixed-metadata adjudication |
| R02 sibling ownership | News and website identity contact follow-up are restricted to the verified host. | Evidence-backed cross-host expansion, explicit path scope and PSL grouping; stricter abstention may reduce recall |
| R03 closed vacancies | Exact-employer ad closure retains source evidence, suppresses carry-forward and emits a closure. Repeat closure is idempotent; reopening emits a new job. Sidebar closure notices are excluded. | More source-specific language and independent job samples |
| R04 dates | Full article timestamps retained, future instants rejected, evaluator cutoff compares full timestamps. | Timezone-free publication timestamps currently rejected |
| R05 financial evidence | Audit-status and accounting-rules locators and semantic checks added. Retained scale replay verifies 48,756/48,756 financial claims with no invalid/unverified claims. | The fresh direct run has 928 filing-history claims outside account-record verification; separate source-type verification is needed |
| R06 scheduling | Immutable account snapshots are prefetched while bulk files load, then consumed once by company workers. Mock batches prove overlap and budget compliance. | Matched live bulk benchmark and separate website verification/enrichment queues |
| R07 request reuse | Bounded equivalent-request coordination reuses only responses passing the freshness gate. No-store responses remain separate. | Live savings measurement and additional timeout/exception stress tests |
| R08 discovery | robots-declared maps and sitemap fallback after exhausted ordinary targets, with bounded detail fetches. | Permitted ATS/HTML adapters, evidenced social aliases and approved NAV access |
| R09 metrics/CI | Independent judgment summarizer, explicit unresolved/unreviewed denominators, Wilson interval, diagnostics in CI and smoke evidence audit. | Independent labels and blinded release evaluation |
| R10 reliability | HTTP fallback restricted to transport failures. Bounded DNS cache with short negative TTL. | Connection-time DNS pinning/rebinding protection |

The retained replay made zero outbound requests and preserved claim content with zero normalizations. Its audit is recorded in [account-locators-audit-20261111.json](../../reports/account-locators-audit-20261111.json). This validates retained source linkage, not population precision.

The new live run returned **100/100 valid envelopes**, using **601 requests, 216.3 seconds and $0 API cost**. It found ten websites, social profiles for three companies, one company article and no jobs. Against the earlier same-cohort direct run, websites increased from nine to ten, requests increased by eight and runtime decreased by 1.7 seconds. Company-news items decreased from two to one. Live source variation and multiple changes prevent attributing these differences to a single fix. Bulk prefetch was not exercised by this direct-mode live run.

The fresh audit passed with 4,522 account claims verified and 928 filing-history claims explicitly unverified at account-record level. It found zero invalid claims or source locators. [Live metrics and comparison](../../reports/remaining-validation100-metrics.json) · [Live evidence audit](../../reports/remaining-validation100-audit.json)

Independent judgments require `organisation_number`, `claim_id`, `reviewer`, `evidence_url` and `judgment`. Allowed outcomes are `supported`, `wrong_entity`, `wrong_value`, `unsupported` and `unresolved`.

```powershell
.venv\Scripts\python.exe eval/adjudication.py RUN judgments.jsonl --output reports/adjudication.json
```

The tool reports precision on resolved sample judgments and separately exposes unresolved and unreviewed claims. It cannot establish reviewer independence or population representativeness. Precision, recall, F1 and competition rank remain unmeasured until independent labels exist. No judgments were fabricated.

## Objective and evidence boundaries

Improve exact-company discovery and refresh without publishing unsupported facts. Prioritize wrong-company publication risks before adding coverage. Keep all outbound requests, retries and discovery calls inside the configured budget. Use permitted sources and explicit missing, blocked and ambiguous states.

The initial review added five offline acceptance cases. Four reproduced then-unresolved defects and one verifies that an unobserved job remains stale without inventing a closure. They initially failed without xfail markers. The implementation pass fixed those defects and promoted the suite into CI. Synthetic failures demonstrate possible behavior, not the frequency of errors in live submissions.

The original 217-case suite passed before this review. The diagnostic baseline completed with **218 passed and 4 failed**, with no setup errors on the workspace-local rerun. All four failures are new acceptance probes. Independent factual precision, exact-company precision, recall, F1 and official score remain unmeasured. Tests and source-integrity audits cannot supply those denominators. The previously recorded scoring contract and submission dates must be checked against the organizer before release; this review did not revalidate the leaderboard or competition schedule.

## Completed work and partial closures

| Previous issue | Current implementation status | Remaining validation |
|---|---|---|
| D01 contact-page identity | Implemented for registered candidates and linked same-host name/contact evidence | Independent ownership review, especially group domains and scoped pages |
| D02/D03 article/job evidence | Retains publication and employer source fragments | Conflicting article signals still bypass the JSON-LD gate through HTML (R01) |
| D04 semantic reference matching | Implemented, scope/currency/period preserved for accounts | Independent reference pool and prediction adjudication are missing |
| D05 missing news in synthesis | Separate unknown for company news implemented | Verify user-facing stale and closure explanations after R03 |
| D06 response reuse | Sequential, bounded, fresh public-response reuse implemented | Concurrent request coalescing is absent (R07) |
| D07 console configuration | Bulk mode and workers validated, passed and reported | Keep CLI/console parity tests during configuration changes |
| D08 sitemap discovery | Bounded linked-sitemap fallback implemented | robots-discovered maps and fallback after unsuccessful ordinary links remain absent (R08) |
| D09 job timestamp expiry | Offset-aware job expiry implemented | Article dates still lose time precision (R04); explicit job closure is lost in refresh (R03) |
| Financial evidence collision | Account locator participates in evidence identity; claim-to-record audit implemented | Extend record-level checks beyond the currently covered subset (R05) |
| Late retry threshold | Lowered admission threshold with finalization reserve | Matched live-scale validation remains outstanding (R06) |

## Priority findings

### R01 — Conflicting article publisher bypasses the HTML path

**P0, reproduced.** `src/signalpost/web.py::_news.from_page` rejects a NewsArticle whose publisher identifier belongs to another company. It then independently evaluates Open Graph publication metadata and HTML time elements. The same detail page with a foreign publisher, `article:published_time` and a heading is published through that fallback.

**Risk:** wrong-company article publication despite explicit conflicting evidence. Existing foreign-publisher tests cover only the structured-data route.

**Remedy:** resolve identity for the candidate article before accepting any extraction route. Associate publisher conflicts with the main article rather than unrelated embedded recommendations. A relevant explicit foreign publisher must block generic HTML fallback. Retain the conflict and abstention reason.

**Acceptance:** the new `foreign-publisher-html` probe rejects the post; add HTML-time equivalents, matching publisher positives, multiple unrelated embedded articles and missing-publisher controls. All routes must enforce the same identity decision. Independently review mixed-metadata group pages before promotion.

### R02 — Sibling hosts inherit article ownership

**P0, reproduced.** `_news.same_site` compares `registrable_domain`. A verified homepage on `fjord.example.no` links to `parent.example.no/news/opening`; a dated article on that sibling host without any exact-company proof is accepted. Root homepage verification sets `scoped=False`, so the destination does not need its own company identity.

**Risk:** a group or sister-company post is attributed to the input company. The exact-number website scan also follows contact pages across a registrable domain, so review that route as a related risk; this review's executable failure covers news.

**Remedy:** carry explicit verified host/path/entity scope in `SiteVisit`. A shared registrable domain is a discovery hint. Require destination identity proof before expanding ownership scope. Preserve legitimate verified language hosts and redirects through explicit evidence. Replace the hand-written suffix approximation with a versioned Public Suffix List implementation for grouping, while keeping legal ownership as a separate decision. The PSL explains why suffix boundaries cannot be determined by a universal string rule. [Public Suffix List](https://publicsuffix.org/learn/)

**Acceptance:** reject unproven parent/sibling/shared-host destinations; allow independently proven same-company hosts. Add group path, tenant-domain, redirect, apex/www and foreign contact-page controls. No permission to publish can come solely from a suffix match.

### R03 — Refresh restores an explicitly closed site vacancy

**P1, reproduced.** `_site_jobs` correctly skips a page containing “Applications closed.” It always marks the jobs family incomplete and emits no item-level negative observation. `refresh.diff` consequently carries the previous ad forward as available with `stale_since`, while its old deadline remains in the future. No `closed_job` change is produced.

**Risk:** a known closure is displayed as a stale vacancy and refresh misses a meaningful event. The passing missing-ad control confirms why ordinary crawl absence must still avoid closure inference.

**Remedy:** emit an evidenced terminal observation keyed by exact employer and canonical ad identity. Apply that observation before incomplete-family carry-forward. Keep historical evidence and expose the closure reason. Scope closure text to the ad, so a sidebar about a different expired vacancy cannot close the current one.

**Acceptance:** explicit closure removes the current ad and emits one evidenced closure; repeating the observation is idempotent. Missing, blocked or unreadable pages remain unknown/stale according to source policy. Add future-deadline, no-deadline, reopening, changed URL and NAV/company-source interaction cases. A `validThrough` date describes validity but does not invalidate an independently observed earlier closure. [Schema.org validThrough](https://schema.org/validThrough)

### R04 — Article timestamps lose publication precision

**P1, reproduced.** `_parse_date` converts timestamps to calendar dates before `_news` compares them with today. At fixture time `2026-11-11T00:00:00Z`, an article dated `2026-11-11T23:00:00Z` is accepted.

**Remedy:** retain original Date/DateTime precision and compare aware instants before deriving any display date. Specify treatment of timezone-free timestamps; do not invent an offset. Preserve date-only inputs as date-only. Schema.org explicitly allows both Date and DateTime for first publication. [Schema.org datePublished](https://schema.org/datePublished)

**Acceptance:** reject future instants, test UTC-midnight offsets and exact boundary instants, preserve date-only positives, reject modified-only dates and retain timestamp evidence. Audit evaluator cutoff logic for the same precision loss before closure.

### R05 — Financial verification remains incomplete

**P1, measured limitation.** The repaired retained scale run checks 42,616 of 48,756 financial claims at account-record level. Another 6,140 remain outside that check. Zero mismatches in the checked subset does not establish correctness of the rest.

**Remedy:** inventory unverified claims by field and source. Add appropriate owner/value/period/scope locators to supported shapes. Verify every claim against its actual source type; do not require an account-record shape for unrelated registry-derived capital data. Explicitly classify unsupported shapes and source omissions.

**Acceptance:** report verified, invalid and unverified counts by field. Mutation tests must detect changed owner, scope, amount, currency and period where applicable. Release targets zero invalid published financial claims and zero silently unverified values. This review did not re-audit the live artifacts.

### R06 — Coverage is constrained by sequencing and unvalidated allocation

**P1, retained measurements plus code inspection.** The earlier 1,100-company diagnosis returned 22 websites, news for five companies and no jobs, with 1,030 website states failed by budget/allocation. Bulk completion precedes the company worker pool. Slow bulk downloads can delay accounts and web work; the revised retry threshold has only fixture validation at scale.

**Remedy:** overlap independent account work with bulk loading, then separate initial website verification from enrichment. Give declared candidates bounded first attempts before deep optional exploration. Reassign unused reservations with global accounting and deadline reserves intact. Keep a dedicated 100-company evaluation experiment; the 1,100-profile submission stress test is a different workload.

**Acceptance:** same cohort/order/configuration A/B with per-phase requests, waiting times, verified company-family gains and failure reasons. Compare direct and bulk paths on compatible observations. For local comparison, use the recorded time/request/cost envelope. For an official run, process the entire organizer-supplied shared batch within its supplied limits; the current contract allows 1,000–1,100 companies. Do not extrapolate scale-cohort coverage into daily recall.

### R07 — Response cache does not coalesce simultaneous requests

**P2, code-inspected.** `Fetcher.get` releases its cache lock before fetching, with no in-flight entry. Two workers missing the same key can both issue outbound requests. The implemented D06 sequential-reuse test cannot establish concurrent deduplication.

**Remedy:** coordinate equivalent eligible requests using bounded per-key in-flight state. Preserve authorization, header, cookie, robots and freshness isolation. Bound follower waiting by the run deadline and release waiters on exceptions. Cache reuse must follow HTTP freshness rules. [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html)

**Acceptance:** synchronized multi-worker fixture performs one eligible fetch; errors, cancellations, different authorization/header contexts and deadline expiry do not deadlock or share unsafe responses. Measure actual saved requests before predicting coverage gains.

### R08 — Discovery remains narrow

**P2, code-inspected.** Sitemap fallback runs only when both ordinary targets and items are empty, and starts from HTML-linked maps. A useless news link suppresses it. Site jobs require JobPosting metadata and limited same-site discovery. Social handle matching omits verified aliases. NAV access remains unavailable in recorded runs.

**Remedy:** add budgeted robots-declared sitemap discovery and fallback after unsuccessful targets; fetch article detail for proof. Develop permitted individual ATS/HTML ad adapters and independently evidenced company aliases. Keep publisher/owner gates common across routes. Treat approved NAV access as an external dependency.

**Acceptance:** incrementally recovered eligible facts on labeled positives, with negatives for product pages, landing pages, parent vacancies, agency handles, sitemap modification dates and blocked sources. No unofficial platform crawler or paid provider is implied by this programme.

### R09 — Evaluation and CI leave blind spots

**P1 for measurement, P2 for CI.** `eval/metrics.py` has semantic positive-pool matching but no independent prediction judgments. Job matching measures ad discovery, not status or date accuracy. Default pytest and `.github/workflows/ci.yml` exclude `eval/diagnostics`; previously fixed diagnostic-only cases can regress without failing default CI. The existing live smoke checks output line count, which does not establish evidence quality.

**Remedy:** label development and blinded release cohorts independently, grouping related entities/hosts to reduce leakage. Keep random companies separate from adversarial or known-positive cases. Record supported, wrong entity, wrong value/date, unsupported and unresolved judgments. Promote fixed diagnostic cases into mandatory CI; keep unresolved probes separately visible and red. Add explicit source/evidence validation to release checks.

**Acceptance:** per-family company recall, claim recall, adjudicated precision, entity precision, evidence sufficiency, stale rate and abstention with numerators, denominators and uncertainty. Compute F1 only from compatible claim-level precision and recall. Unresolved judgments remain explicit. No estimated competition rank until an independent benchmark exists.

### R10 — Smaller reliability and reporting gaps

**P2/P3, inspected.** Website HTTPS fallback currently retries HTTP after permanent HTTP errors as well as transport failures. DNS public-address decisions are cached process-wide without expiry and are separate from connection-time resolution. Review wasted fallback requests, stale DNS failures and rebinding protection. These are code risks, not demonstrated live incidents in this review.

**Remedy and gates:** restrict transport fallback by error class with 403/404/timeout controls; define DNS cache lifetime and validate the actual connection destination through the transport boundary. Add bounded tests before changing network policy. Preserve successful public-host behavior and count every outbound attempt.

The programme itself contained obsolete open counts and missing-cache statements after fixes had landed. This revision replaces those statuses. Keep historical reports dated, and maintain a single current result table.

## Implementation order and promotion gates

1. Fix R01/R02 identity scope, with mixed-source and host-boundary regression controls.
2. Fix R03/R04 lifecycle and timestamp precision; add two-run refresh tests and user-visible closure handling.
3. Extend R05 verification and create R09 independent labels. Promote fixed diagnostics into default CI.
4. Run R06/R07 scheduling and request-reuse experiments individually on frozen cohorts.
5. Add R08 discovery routes only when they improve independently supported coverage. Address R10 network reliability alongside those changes.

For every item use `observed → reproduced → implemented → regression passed → independently validated → promoted`. Code inspection alone is a risk finding. A passing synthetic case closes the local defect but does not establish live precision. Record code hash, cohort hash, configuration, source observation time, label version and all failed experiments. The initial diagnostic review made no live crawl. The later implementation pass performed the separate 100-company validation summarized above.

## Reproduction and historical diagnostic result

```powershell
# Use a fresh workspace-local directory for each run if the system temp directory is inaccessible.
.venv\Scripts\python.exe -m pytest tests eval/diagnostics -q -p no:cacheprovider --tb=short --basetemp=.test-tmp/remaining-review-next --junitxml=.test-tmp/remaining-risks-next.xml

# Follow-up acceptance probes and controls, now passing
.venv\Scripts\python.exe -m pytest eval/diagnostics/test_remaining_risks.py -q -p no:cacheprovider --tb=short
```

New probes live in [test_remaining_risks.py](../../eval/diagnostics/test_remaining_risks.py). The expanded run's JUnit artifact is `.test-tmp/remaining-risks.xml`. **Result: 222 cases, 218 passed, 4 failed, 0 errors in 36.27 seconds.** The original 217 cases still pass, plus the new missing-ad control. The initial attempt hit a Windows permission error in the shared pytest temp directory; the workspace-local rerun separates that environment issue from product failures.

## Website pilot completed — 12 November 2026

See [pilot measurements and diagnosis](../../reports/website-pilot-20261112.md). A fresh 100-company cohort and 82 initial candidates are available locally, with 100 blank independent review tasks. The org-only baseline produced 23 websites, 9 social-profile companies and 100 valid outputs in 239.6 seconds / 1,137 requests. No probe-accepted website was missed by the baseline. Prioritize independent labels for 23 publications, 61 unresolved candidate cases and 16 no-candidate cases before tuning discovery or attribution. All 275 unique Python tests pass. Precision/recall are not yet measured; the larger corpus, extraction-only harness and held-out evaluation remain pending.

## Scheduling checkpoint — 13 November 2026

The first implementation increment is described in [the scheduling report](../../reports/scheduling-improvement-20261113.md). Breadth-first rounds are opt-in; the default retains existing allocation until independent review and matched validation. The scale experiment published 38 websites versus 29 historically at 1,920 requests, but lost three earlier websites and took longer. Identity traversal now fails closed on interruption. Both frontend surfaces expose attempt/completion/budget diagnostics without calling them accuracy. Remaining programme items and promotion gates are in [the root plan](../../plan.md).
