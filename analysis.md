# SignalPost analysis

> **14 November update:** follow the [recovery validation](reports/recovery-validation-20261114.md) for current
> changes and measured limits. Targeted safeguards now reject and revoke the disclosed OTIS India claims and
> reject utility pages as news. Only two organizer examples were disclosed; independent accuracy remains unknown.
> The analysis below is historical and its metrics are not current-source measurements.

**11 November 2026** · Diagnosis, implementation and verification of the accuracy improvement programme.

The most consequential defect was in financial evidence attribution. Eleven published claims pointed to the wrong account scope even though their values agreed with the cited records. The old audit passed because it checked whether a locator resolved to its recorded value. The revised audit also checks whether the locator supports the published claim. It rejects all 11 original mismatches. After re-extracting the evidence from the same retained sources, it verified all 42,616 claims carrying account-record pointers. All 1,100 envelopes preserved their claim content and produced zero refresh changes.

The completed work also tightens article and vacancy publication, improves website and news discovery, and addresses request reuse and console configuration. All **217 automated cases passed**, including the previously failing diagnostics. A separate live 100-company run returned all 100 envelopes. Independent precision and recall and the full-scale live effect of the fixes still need measurement.

## 1. What SignalPost evaluates

SignalPost takes Norwegian organisation numbers and returns a terminal envelope for each company. An envelope contains published claims, source evidence, availability states, and refresh information. It can include registry identity, financial statements, roles, workplaces, relationships, websites, social profiles, dated activity and vacancies. The collector resolves the legal entity before publishing company-specific web facts. It records source access and uncertainty through the availability states.

The evaluation uses four kinds of evidence:

| Check | What it establishes | What it leaves open |
|---|---|---|
| Offline regression and diagnostic fixtures | The tested behaviors are reproducible, including rejection of specific wrong-company, expiry and publication-date cases. | How often the defects or missed opportunities occur across real companies. |
| Live collection | Completion, observed company coverage, source availability, runtime and request count for the supplied batch. | Whether the collector found every eligible fact or every fact is correct. |
| Retained-source audit | Whether retained evidence resolves and whether checked financial claims match their account records. | Full-page support for excerpt-only sources and claims without appropriate locators. |
| Refresh replay | Whether unchanged claims produce false business changes and whether controlled changes are detected. | Freshness and coverage after real source changes or outages. |

The source policy permits public registry and company-owned research within the configured request and time limits. NAV requires approved access. The evaluated runs made zero NAV feed requests because an approved credential was unavailable. The agent uses deterministic extraction and synthesis, and the recorded external API cost was $0. [Source policy](SOURCES.md)

## 2. Evaluation timeline and reproducibility

The 1,100-company live diagnosis used the same ordered engineering cohort as the retained comparison. The cohort has been used before and is useful for repeatable engineering comparisons. The 100-company validation cohort used direct registry lookups. It exercised the main fixes before the final legal-form guard and console display adjustments. The final test suite exercised the completed working tree.

| Run | Input and configuration | Scope of verification |
|---|---|---|
| Retained comparison | 1,100 companies, bulk roles and workplaces | Historical operating and coverage comparison |
| Live diagnosis, `run-20261111T091855Z` | Same 1,100 companies, bulk roles and workplaces, eight workers, seven-day job window, 2,000 request cap and 15-minute limit | Live collection before the latest accuracy fixes |
| Account evidence repair | Retained sources from the live diagnosis, accounts-only replay | Evidence repair and comparison of all 1,100 envelopes |
| Live validation, `run-20261111T093741Z` | 100 companies, direct mode, eight workers, seven-day job window, 900 request cap and eight-minute limit | Live integration check after the main fixes |

Both live runs recorded a working-tree revision based on `de11bc45be98`. The scale diagnosis reported code SHA-256 `badf1d5a3a6f6834a3a7fc276b162b477b65a6ecff89f372d01640d8cd0a9700`. The validation run reported `d822638ebeeb79b302280c3b0f4304fb615246d17abfc5ad577b80e11cdd6d24`. The replay report retains the original run ID and operating measurements and records its own replay metadata. Its 1,742 request count describes the original collection. The replay itself performed zero outbound requests.

## 3. Financial accuracy and evidence linkage

### Failure mechanism

Before the fix, evidence identity depended on the source URL and response digest, the quoted value, the extraction method and the reporting period. Company accounts and consolidated accounts can appear in the same response and contain the same value for the same field and period. In that case both records generated the same evidence ID. The first evidence object won, and both claims could resolve to the first record.

For organisation `985446474`, the 2024 `long_term_debt` claims for `SELSKAP` and `KONSERN` both referenced `ev-92a47778f9c94a68`. Its locator pointed to the consolidated record. The published values agreed with their source amounts, while the company-level claim cited the consolidated record. The same defect affected 11 claims in the 1,100-company live diagnosis.

The former snapshot audit verified source integrity and the locator's stored value. A test could change the published amount, currency or period while leaving the locator and retained response intact. The old audit passed each mutation. The wrong-scope evidence also passed all 75,337 standard evidence checks on the live diagnosis batch.

### Repair and result

Account evidence IDs now include the account-record locator. The locator carries the organisation number, currency, period and account scope when the source provides it. The audit follows the referenced account record and checks the published claim's field path, owner, amount, currency, period and scope. Older evidence without a suitable record pointer or explicit attribution remains visible in the unverified count.

| Account audit measure | Original live diagnosis | Repaired retained output |
|---|---:|---:|
| Current financial claims | 48,756 | 48,756 |
| Claims with account-record pointers | 42,616 | 42,616 |
| Claims verified against the referenced record | 42,605 | 42,616 |
| Wrong-scope record associations | 11 | 0 |
| Financial claims outside record-level verification | 6,140 | 6,140 |

The revised audit rejected the original output and passed the repaired output. The final repair passed **75,027 locator checks** and **321 excerpt-integrity checks**, with zero missing references, invalid objects or invalid locators. The accounts-only replay preserved all claim fields other than evidence references and kept nonfinancial claims identical. Comparing the original and repaired envelopes through refresh produced zero changes.

Record-level verification covers about **87.4%** of the financial claims in this batch. The remaining 6,140 include financial facts that lack account-record locators. Extending explicit source binding to those facts remains an accuracy improvement. The 42,616 checks establish the provenance of the tested claims against the retained source records. They do not estimate population precision.

## 4. Publication and coverage defects

| Area | Reproduced behavior | Implemented change |
|---|---|---|
| Vacancy expiry | An offset timestamp could be truncated to a calendar date and leave an expired ad active. | Preserve timezone-aware deadlines through website jobs, NAV and refresh. Date-only deadlines retain UTC calendar-day semantics. |
| News and job evidence | An excerpt could retain the title without the source fields that supported the publication date or hiring identity. | Retain original date and publisher fields where available. Retain employer and job dates, plus active status for NAV ads. The verifier recognizes structured fragments and explicit HTML publication markers. |
| Exact legal identity | Name-only checks treated `AS` and `ASA` as equivalent for a vacancy or article publisher. | Preserve legal-form tokens in name-only matching. Reject conflicting organisation numbers and explicit legal-form conflicts in website identity checks. |
| Closed vacancy | Recent structured metadata could qualify a vacancy whose detail page explicitly said applications were closed. | Reject recognized closure text. Use a valid deadline or a current application signal for no-deadline website ads, with a recency bound. |
| Article date | A time element with `class="unpublished"` qualified because the code matched `published` as a substring. | Require an explicit publication marker and reject negative or modification markers. |
| Contact-page identity | A registered candidate with a brand homepage remained ambiguous even when its linked contact page carried the exact legal name and corroborating registry contact. | Check linked contact pages on the same host and bind identity and corroboration to the same page. Existing conflicting-owner checks still apply. |
| Missing company news | A registry event made the activity family available and hid unknown company news in the brief. | Report company news as a distinct unknown when no dated company article was verified. |
| Sitemap discovery | A valid article reachable only through a linked sitemap was missed. | Use bounded same-host sitemap discovery and verify each article on its detail page. Sitemap modification dates supply no publication evidence. |
| Repeated fetches | Identical cacheable requests consumed more than one outbound request. | Reuse eligible fresh public responses within the run. Authenticated, conditional, private, stale and context-different responses are excluded by the tested rules. |
| Console configuration | The console omitted requested bulk mode and worker count. | Validate and pass both settings to the CLI and record the effective configuration in the run report. |
| Local recall matching | An identical reference fact missed when the reviewer assigned a different internal key. | Match semantic facts within the exact company and field. Preserve scope, currency and period for account matching. Use item identity for article and vacancy discovery metrics. |

The wrong legal form, closed vacancy and unpublished article failures were reproduced in controlled cases. Those cases identify possible failure modes, and their live frequency remains unknown. Site closure markers and metadata are source-dependent. Vacancy discovery metrics identify the same ad and employer and do not replace checking current status and every reported date.

## 5. Live coverage and operating behavior

| Measure | Retained 1,100-company comparison | 1,100-company live diagnosis | 100-company live validation |
|---|---:|---:|---:|
| Terminal envelopes | 1,100 | 1,100 | 100 |
| Identity and leadership, companies per family | 1,098 | 1,098 | 99 |
| Companies with financials | 1,091 | 1,091 | 99 |
| Companies with registered workplaces | 839 | 839 | 75 |
| Companies with group relationships | 78 | 8 | 6 |
| Companies with verified websites | 28 | 22 | 9 |
| Companies with social profiles | 10 | 9 | 3 |
| Companies with dated company news | 5 | 5 | 1 |
| Companies with verified jobs | 0 | 0 | 0 |
| Outbound requests | 1,920 | 1,742 | 593 |
| Elapsed time | 407.4 s | 702.0 s | 218.0 s |
| Declared external API cost | $0 | $0 | $0 |

The 100-company run emitted **8,449 claims** and found **two articles for one company**. Its artifact audit passed 7,812 locator checks and 47 excerpt checks. It verified 3,956 financial claims against account records and reported 1,494 outside record-level verification. The 100-company run used a different cohort and configuration, so its 9% website coverage should be read as an integration result. A matched repeat of the large live batch is needed to estimate a coverage gain.

The large live diagnosis emitted **82,669 claims**. Website results were 22 available, 34 ambiguous, seven blocked, seven unavailable and 1,030 failed due to request allocation or exhaustion. Sixteen verified websites cited an organisation number. Six used other accepted identity signals. The 1,030 failures measure an execution constraint and leave the presence of eligible websites unresolved.

### Why the large run left requests unused

The role and workplace bulk operations took 543 and 302 seconds and overlapped. The company phase finished near 691 seconds. The run had a 900-second limit and a 72-second safety reserve, leaving roughly 137 seconds under its operational deadline. The old final retry pass required 180 seconds of headroom and skipped the retry. The run left 178 requests below its 1,920 usable request cap.

The earlier run spent 178 requests in its retry pass and recovered 70 group states and 58 website states. That difference explains the loss of the retry opportunity in the slower run. Source variation and fetch ordering can also affect individual websites. The revised retry pass can start with 90 seconds of headroom and stops admitting work before the finalization reserve. A fixed-clock test covers the observed 137-second scenario. Live scale coverage after this change remains unmeasured. Overlapping account work with a delayed bulk download remains an experiment.

## 6. Test and score interpretation

The diagnosis ran **208 cases**, with **195 passing and 13 failing**. The failing cases included five open improvement probes and eight newer accuracy probes. The final suite ran **217 cases**, all passing, with additional checks for financial field and scope mutations, legal-form boundaries and request reuse. The console smoke test passed. The prior live diagnosis, the repaired retained replay and the 100-company validation all returned one envelope for every input.

| Metric | Current interpretation |
|---|---|
| Completion | 1,100/1,100 on the live scale diagnosis and retained repair. 100/100 on live validation. |
| Evidence integrity | Passed on both audited runs after applying the relevant audit checks. The original live diagnosis fails the new claim-to-record audit with 11 scope mismatches. |
| Financial claim-to-record linkage | 42,616 verified after repair. Another 6,140 financial claims remain outside that verification. |
| Refresh | Zero changes across the 1,100 original and repaired envelopes. The earlier controlled mutation replay passed its checks for idempotence, typed changes and carry-forward on unavailable sources. |
| Observed coverage | Measured per company and field. Registry families are well covered. Website, dated news and jobs remain sparse in the scale diagnosis. |
| Exact-company precision and claim recall | Unmeasured. The engineering cohorts lack independent adjudication and a reference set of eligible facts. |
| Official score | Unmeasured. Test passes, locator checks and observed coverage cannot be converted to a competition score. |

The next useful measurement is a matched 1,100-company live rerun using the final code, alongside an independently labeled sample. The matched rerun can quantify the time and request changes. The labeled sample can quantify exact-company precision and recall, with separate reporting for random companies and difficult or known-positive website, news and job cases. Every sampled judgment should retain the organisation number, source, relevant date, claimed fact and adjudication outcome.

## 7. Reproduction commands and artifacts

Run from the repository root. Choose a fresh output directory when collecting new observations. The replay command assumes the original scale output is available locally.

```powershell
# Regression and diagnostic cases
uv run --frozen --group dev pytest tests eval/diagnostics -q -p no:cacheprovider

# Fresh 1,100-company live comparison
uv run --frozen signalpost run --organisations eval/rankup/scale-1100.jsonl --out out-programme-scale1100-next --bulk-files --workers 8 --job-days 7 --max-requests 2000 --max-minutes 15 --max-cost 10 --no-showcase

# Rebuild account evidence from the recorded live sources and audit it
uv run --frozen python eval/replay_registry.py out-programme-scale1100 out-programme-scale1100-repaired --accounts-only
uv run --frozen python eval/snapshot_audit.py out-programme-scale1100-repaired

# Reproduce the 100-company validation configuration
uv run --frozen signalpost run --organisations eval/rankup/validation-100.jsonl --out out-programme-validation100-next --workers 8 --job-days 7 --max-requests 900 --max-minutes 8 --max-cost 10 --no-showcase
```

The source diagnosis and plan record the individual failure cases and their acceptance gates. [Batch diagnosis](docs/dev/batch-accuracy-diagnosis.md) · [Fix plan](docs/dev/batch-accuracy-fix-plan.md) · [Improvement programme](docs/dev/metrics-improvement-plan.md)

Local run reports contain the recorded inputs, timings, limits and provenance. Generated run directories are local artifacts. [Scale diagnosis](out-programme-scale1100/run-report.json) · [Repaired retained run](out-programme-scale1100-repaired/run-report.json) · [Live validation](out-programme-fixes-validation100/run-report.json)

## Follow-up review — remaining risks

A subsequent working-tree review on 11 November added five offline cases. The combined suite now reports **218 passed and 4 failed** across 222 cases. The four new failures reproduce foreign-publisher HTML fallback, ownership inherited across sibling hosts, future article timestamps truncated to dates, and refresh carrying forward an explicitly closed site vacancy. The previous 217 cases remain green. These findings supersede any interpretation of the earlier all-green result as comprehensive accuracy validation. Live prevalence remains unknown.

The updated [improvement programme](docs/dev/metrics-improvement-plan.md) records ten prioritized findings, their evidence strength, affected code, remedies and acceptance gates. It also covers incomplete financial verification, scheduling, concurrent fetch reuse, narrow discovery, independent metrics and CI gaps. Production behavior was unchanged during this follow-up review.

## Implementation follow-up — 12 November 2026

The four follow-up failures are fixed. The final combined suite passes **255 cases**, including the direct/bulk batch fixtures up to 1,100 companies. CI includes all diagnostics. The implementation also adds concurrent request coordination, robots/sitemap recovery, account/bulk overlap, stricter HTTP fallback, bounded DNS caching and independent judgment tooling.

Re-extraction of retained scale sources now verifies **48,756 financial claims**, including 3,070 audit-status and 3,070 accounting-rules claims previously outside record-level verification. There are zero invalid or unverified financial claims in that retained batch and zero replay normalizations. This is source-linkage validation, not an estimate of factual population precision.

Fresh live validation returned **100/100 valid envelopes**, **601 requests**, **216.3 seconds**, and **$0 API cost**. Websites increased from nine to ten in the same-cohort comparison. Social coverage stayed at three companies; company news decreased from two items to one, for one company; jobs remained zero with NAV blocked by missing approved access. The audit verified 4,522 account claims and identified 928 filing-history claims still outside that verification. All source-integrity checks passed. The live run used direct mode, so it does not measure the bulk-overlap improvement.

The current [improvement programme](docs/dev/metrics-improvement-plan.md) distinguishes implemented fixes from remaining work, including independent labels, filing-history verification, matched bulk validation, broader permitted discovery and connection-time DNS protection. The live run retains its original UTC identifier `run-20261111T100540Z`; this follow-up is dated using the client calendar.

## Push-readiness pass — 12 November 2026

The final suite now passes **267 tests** under pinned Python 3.12, with successful clean installation, console smoke and refresh replay. Filing-history source checks close the 928-claim verification gap in the direct sample. Website verification and optional enrichment now run in separate stages.

The fresh scale run completed **1,100/1,100 envelopes**, **1,920 requests**, **429.3 seconds**, **$0**, with **29 websites**, social profiles for **11 companies**, and **78 companies with group facts**. Its audit verified **48,707 financial claims** with zero invalid/unverified claims. The fresh direct smoke completed **100/100**, **607 requests**, **220.1 seconds**, **$0**, with **11 websites**. Its audit verified **4,522 account claims plus 928 filing-history claims**.

Scale news coverage fell to two companies. Inspection exposed a publisher-reference false negative; resolving unique same-page Organization references recovered three articles for Gode Tall AS in a separate final-code check. The larger runs preceded that correction. Independent precision/recall and competition score remain unknown. See the [release report](reports/release-readiness-20261112.md) for provenance, comparison caveats, private output locations and remaining work. No commit or push was made.
