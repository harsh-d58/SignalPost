# Deep website discovery and bulk evaluation plan

12 November 2026. Planning artifact only: no new bulk crawl, paid provider, production change or independently verified website list is created by this document.

## 1. Objective

Build a benchmark of **1,500 distinct Norwegian legal entities paired with candidate websites**, targeting up to **3,000 deduplicated candidate URLs**. The counts are collection targets, not assertions that every company has an official site. Independently establish ownership and eligible facts, then test discovery, attribution, extraction and refresh separately.

The latest engineering scale run returned 29 verified websites from 1,100 inputs. Its website states were 29 available, 44 ambiguous, 12 blocked, 42 not_available and 973 failed. Of the failures, 968 explicitly stopped at the website phase budget. Missing outputs therefore cannot be labeled as companies without websites. The earlier score estimate was an illustrative scenario, not benchmark evidence.

The organizer evaluates code against a shared company batch and a checked reference collection. Local reference labels should be versioned, and our local results must remain distinct from official recall. [Evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md)

## 2. Build three separately reported cohorts

| Cohort | Distinct entities | Selection | Purpose |
|---|---:|---|---|
| Random eligible companies | 1,000 | Seeded draw from the official universe, excluding previously inspected companies | Representative discovery and execution baseline; research eligibility independently |
| Known-positive website cases | 300 | Independent researcher identifies exact-company sites before the crawler sees them | Measure missed discoveries and extraction failures where eligible evidence is known |
| Attribution and access challenges | 200 | Deliberately select confusing ownership and access situations | Test safe abstention, wrong-company rejection and source-policy handling |
| Total | 1,500 | Deduplicate org numbers across cohorts; preserve cohort provenance | Never merge these strata into a population accuracy headline |

Within the 300 positive cases, aim for 100 with an eligible dated article, 100 with an independently verified active individual vacancy, and 100 other verified sites. Assign one primary bucket per company even when it has multiple fact families. If fewer active vacancies can be independently verified, report the actual denominator and shortfall; do not substitute careers landing pages.

Allocate the 200 challenge cases initially as 80 parent/subsidiary/franchise/shared-domain cases, 50 trading-name or rebrand cases, 40 agency/theme/directory-link cases, and 30 generic-name or access/redirect cases. Cases may have secondary tags. Include both positive and negative outcomes within these categories, so a company in a group is not automatically labeled negative.

Cover a spread of industries, municipalities, legal forms, employee bands, Norwegian characters, multilingual sites and organization sizes. Avoid a benchmark dominated by prominent listed companies or one CMS.

Select 100 entities from these cohorts for repeated refresh observations. These are repeats, not another 100 unique companies.

## 3. Search and source-discovery sequence

### Stage A — establish the company identity

For every org number, obtain its current legal name, legal form, address, registry website, corporate email domain and known group/subunit relationships. Preserve the source retrieval time. Use the public universe for sampling, not as a current legal-identity record. Registry entity, subunit and bulk endpoints are documented by Brønnøysundregistrene. [Official API documentation](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html)

Check the supplied archive's decompressed SHA-256 against the published corpus hash before freezing the batch. Locally supplied archive: `C:\Users\HP\Downloads\signalpost-company-universe-2025.jsonl (1).gz`.

### Stage B — collect candidates cheaply

Use these routes in order:

1. Registry-declared website.
2. Corporate email domain, excluding free-mail providers and known accountant/agency domains.
3. Declared workplace/subunit website or email domain, retained as a separate relationship until legal-entity scope is established.
4. Wikidata website candidate joined through the exact organization number.
5. Independently researched candidates using the query sequence below.
6. Bounded legal-name domain guesses as the final fallback.

Record all routes that found the same candidate. Do not drop a candidate merely because its spelling differs from the legal name; send it to the identity gate. Normalize IDNs, fragments and default ports, but do not collapse different hosts, tenants or company-specific paths into one owner.

### Stage C — targeted deep searches

For unresolved companies, a researcher or an explicitly approved search API runs queries in this order. Braces represent fields substituted from the registry record.

```text
"{orgnr}"
"{orgnr formatted as three groups}" kontakt
"{exact legal name}" "{municipality}"
"{exact legal name}" (kontakt OR "om oss" OR "personvern")
"{exact legal name}" (nyheter OR aktuelt OR pressemelding)
"{exact legal name}" (karriere OR "ledige stillinger" OR jobb)
site:{candidate_host} "{orgnr}"
site:{candidate_host} "{exact legal name}"
```

Use two initial queries per unresolved company and a third only when the first two reveal a plausible candidate. Query syntax depends on the selected service; unsupported operators must be translated or omitted. Review a bounded result set, deduplicate candidates and fetch the actual permitted source page. A search snippet never becomes claim evidence.

No search API is currently configured in this repository. Start with registry and company-owned sources. An API connector is a separate declared implementation experiment with documented access terms, request accounting and current pricing. Do not scrape search-result HTML or restricted platforms as a shortcut.

### Stage D — inspect ownership evidence

For each candidate, inspect the homepage and up to two linked legal/contact pages. Prefer footer ownership statements, contact details, legal notices, privacy-controller identity and source Organization metadata. Distinguish the page operator from a mentioned customer, supplier, founder or web developer.

A strong acceptance case is the exact org number in an ownership context without conflicting owner evidence. Name-based acceptance needs the exact legal identity plus independent registry corroboration. Related-group domains remain labeled relationships. Subsidiary pages prove only their evidenced entity/path scope; that proof does not authorize parent news, jobs or socials.

Store the proof page, quotation/source fragment, retrieved time, content hash, identity method and verified scope. An arbitrary weighted name-match score must never override a contradictory org number.

### Stage E — discover useful pages after ownership verification

Inspect robots-declared and HTML-linked sitemaps, one relevant feed, and navigation links. Prioritize contact/legal pages, dated news detail pages and single-job detail pages. Include Norwegian path patterns such as `kontakt`, `om-oss`, `nyheter`, `aktuelt`, `karriere` and `ledige-stillinger`.

For initial research, allow at most two sitemap documents, three news details and three job details per verified entity. Follow deeper only when the first pass finds a specific evidence lead and the development budget allows it. Bound XML size, redirect hops and depth; reject XML external entities and cycles. A sitemap's `lastmod` records modification, not original publication. [Sitemap protocol](https://www.sitemaps.org/protocol.html)

Job and social discovery must retain the current exact-employer and matching-handle gates. An ATS may host a legitimate ad externally, but its permitted access and employer attribution must be checked independently. A blocked platform remains blocked; a credential is not assumed to grant unrestricted redistribution rights.

## 4. Dataset and label contract

Use one candidate row per `(organisation_number, candidate_url)` with:

- Cohort, split, primary challenge type and secondary tags.
- Current legal name and dated identity-source identifier.
- Candidate URL, discovery route/query, requested URL and final URL.
- Parent/group identifier where independently known; normalized host and path scope.
- Access state and permitted access method.
- Ownership judgment: `exact_entity`, `related_entity`, `unrelated`, `unresolved`, or `blocked`.
- Reference facts with fact family, canonical detail URL, value, publication/expiry/reporting dates and time precision.
- Evidence URLs, source fragments, retrieval timestamps, hashes and reviewer identity.
- Review status, disagreement resolution and reference-pool version.

Do not label a company `no_website` because the crawler failed. Use `no_eligible_site_found_within_research_scope` where appropriate. Unknown, blocked and unresolved cases must remain visible.

Keep reference facts separate from prediction judgments. The crawler's previous output can seed regression cases, but it cannot be its own recall ground truth. Review all proposed ownership positives and all hard negatives; use a second reviewer for disputed or group-scope cases. If only one reviewer is available, explicitly label the set singly reviewed.

## 5. Avoid leakage

Allocate approximate 60% development, 20% validation and 20% blinded release splits before implementation experiments. Assign connected ownership/domain groups together, then report actual counts because group boundaries may prevent an exact 900/300/300 split. Keep each original cohort's distribution visible within the split.

Group by independently known corporate relationships and registrable domain using a versioned Public Suffix List, with explicit treatment of private hosting suffixes and tenant identities. PSL boundaries help group domains; they do not establish legal ownership. [Public Suffix List](https://publicsuffix.org/learn/)

Existing `eval/freeze_cohorts.py` only groups exact known hosts and must be extended before calling its splits group-isolated. Exclude all inspected org numbers from existing `eval/*.jsonl`, `eval/rankup/*.jsonl` and prior local run inputs when constructing the new release split. Keep previously inspected examples in a separate regression set.

The researcher may see release sources to create labels, but the implementation process must not receive those labels until the frozen revision is evaluated. If the same agent sees and optimizes against every label, call the set development data, not blind.

## 6. Run three diagnostic modes

| Mode | Input | Separates |
|---|---|---|
| Discovery | Org numbers only; hide reference URLs | Missing candidates, request allocation and identity verification |
| Attribution | Org number plus researcher-supplied candidate URL, including decoys | Exact-company decisions without discovery confounding |
| Extraction | Already independently verified source scope and retained permitted pages | News/job/social extraction without discovery confounding |

The current CLI supports discovery mode. Candidate injection and a retained-page extraction harness are proposed additions, not existing command flags. Injected URLs must never be supplied to an end-to-end discovery score. All three modes must continue to enforce source access and evidence rules.

For extraction tests use offline snapshots only where retention is permitted. Otherwise use minimal supported fragments and clearly mark limitations; do not pretend excerpts establish full-page context.

## 7. Budget and execution

Start with a **100-company development pilot**: 40 positives, 40 challenge cases and 20 random entities. Use the pilot to calibrate source yields, request costs and label quality. Then evaluate the full 1,500 as fifteen 100-company chunks and separately run an official-like 1,100-company batch drawn from the random pool plus explicitly declared additional random entities. Do not fill an allegedly random scale batch with targeted positives.

A proposed 100-company experimental request allocation is:

| Lane | Maximum initial reservation |
|---|---:|
| Official identity, accounts, roles and locations | 550 |
| Website candidates and identity verification | 650 |
| News details | 200 |
| Job details | 150 |
| Optional approved search API discovery | 100 |
| Shared retries/completion work | 270 |
| Unspent safety reserve | 80 |
| Total hard ceiling | 2,000 |

These are experimental ceilings, not measured optimums. Every robots request, redirect and retry consumes the shared budget. Release the search reservation if no approved connector exists. Preserve the finalization time reserve and record actual per-phase spending. Use the organizer's supplied official limits when they differ from local experiments.

For 1,100 companies, roughly 1,100 account requests alone leave fewer than 900 of a 2,000-request envelope before the other official sources and safety reserve. A fresh robots-plus-homepage visit can consume two requests before ownership follow-up. Consequently, attempting every company website under that budget is generally infeasible. Measure candidate prioritization and supported coverage per request; do not promise full website coverage by raising crawl depth.

Dataset construction is a separate development workload. Plan and cap each research chunk independently, record cumulative requests/costs across chunks, and do not claim a fifteen-chunk research run meets a single official run's limits. There is no approved paid-provider spend in this plan.

## 8. Failure taxonomy and measurements

Record one main failure stage plus secondary causes for every missed reference opportunity:

`candidate_not_generated`, `not_attempted_budget`, `blocked_policy`, `unreachable`, `wrong_owner_rejected`, `unresolved_owner`, `false_identity_rejection`, `detail_not_discovered`, `unsupported_markup`, `invalid_or_missing_publish_date`, `expired_job`, `evidence_not_retained`, `refresh_incorrect`.

Report separately:

- Candidate recall among independently labeled website positives.
- Ownership precision and false rejection rate, with reviewed denominators.
- End-to-end company website recall and detail-fact recall.
- News/job publication-date, employer and status correctness.
- Per-stratum abstention, blocked rate, attempted rate and budget failures.
- Newly supported company/family pairs per 100 outbound requests, latency and declared cost.
- Refresh detection lag, incorrect removals and stale retention.

Use confidence intervals for reviewed estimates and report the sampling design. Zero observed errors in a small sample is not proof of perfect precision. Do not calculate population precision from the targeted hard-case set or call website prevalence a recall score.

## 9. Required adversarial cases

Include parent-site redirects; a subsidiary mentioned in customer lists; franchise branches; AS versus ASA; recycled domains; shared accountants; footer agency links; same-name companies in different municipalities; IDN names; apex/www redirects; company pages under a group path; social share URLs; bare JSON-LD publisher references; duplicate/conflicting graph nodes; unrelated embedded recommendations; sitemap-only news; product pages with Article markup; dateModified-only posts; future and timezone-free timestamps; careers landing pages; external ATS ads; wrong employers; expired ads; closed notices in sidebars; 403/429 responses; robots blocks; redirect loops; malformed/oversized XML; and private-address/rebinding destinations.

Refresh 100 selected entities at baseline and later declared intervals, such as 24 and 72 hours. These are a proposed test schedule, not an automation. For live sites with no observed changes, report no test opportunity. Use controlled fixtures to test specific changes and keep those outcomes separate from live freshness measurements.

## 10. Delivery order and promotion gates

1. Build the candidate ledger and a source-access registry; freeze cohort provenance and code revision.
2. Complete the 100-company pilot labels and verify positive/negative controls.
3. Add diagnostic-mode harnesses and structured failure-stage counters.
4. Compare the current baseline with one discovery change at a time on development data.
5. Expand to all chunks, retaining per-cohort metrics and sampling denominators.
6. Freeze the strongest revision and run the withheld release set once. Do not tune on that release set afterward.

Proposed engineering acceptance targets, not predictions or organizer rules: zero observed material wrong-company publications, zero fabricated financial values, source support for every accepted test claim, at least a 10-percentage-point improvement in discovery recall on labeled positives over the same-budget baseline, and no increase in wrong-entity rate. Require complete terminal output within the chosen limits. Any disputed material publication blocks promotion until resolved. If baseline recall is already near ceiling, use a prespecified missed-opportunity reduction target instead.

## 11. Artifacts to create

Pilot tooling implemented: `eval/build_website_corpus.py` freezes the 100-company corpus; `eval/website_modes.py` probes injected candidates; `eval/website_metrics.py` compares probe observations with org-only baseline output. Extraction-only and scored independent-label modes remain to be implemented.

Keep private candidate ledgers, source fragments, judgments and cohort inputs under `out-website-benchmark/`. Publish only appropriate aggregate reports under `reports/`. Expected artifacts: candidate ledger, disjoint cohort manifests with hashes, source-access decisions, reference facts, prediction judgments, failure matrix, matched-budget comparisons and refresh results.

Reuse existing `eval/prepare_review.py`, `eval/adjudication.py`, `eval/snapshot_audit.py`, `eval/metrics.py` and the regression suites where their scope fits. The existing review exporter samples predictions; it does not collect missing reference facts.

Immediate next action: construct and label the 100-company pilot, with the 968 budget-unattempted cases informing allocation experiments but not becoming the new blinded set. Build the large benchmark from fresh eligible entities, not just a list of popular Norwegian brands.

## 12. Pilot execution status (12 November 2026)

The first 100-company development pilot is built under `out-website-pilot/`, with 82 universe website candidates and 3,722 previously tested entities excluded. The decompressed universe hash was verified. Its 40 positive-candidate cases are provisional, not known-positive labels. All ownership judgments remain blank. See `reports/website-pilot-20261112.md` for measured runs and next steps. The 1,500-company benchmark and withheld release set are not yet built.
