# SignalPost organizer-result diagnosis — 14 November 2026

**Release decision: blocked. Current code still publishes a wrong-company website/description and misclassifies contact/careers pages as news.** This is a diagnostic baseline, not a claim that the defects below have been fixed.

## 1. Version and scoring facts

The organizer evaluated `eaef80456aa6954b40a969892945b4d448e738f7`. The inspected local `main` HEAD is `11eee14f62de53c42904541f923a39677ce7fc41`. The live diagnostic reports identify source digest `537e1d16f3a4296887226e831413accf2802b64463120d08d99fbea522a3b9f1`. Later work is substantial, but it was not included in that official result. A push alone does not update the organizer's frozen version.

| Official result for the old commit | Value |
|---|---:|
| Rank | 100 / 104 scored entries |
| Total | 24.58 / 100 |
| Recall points | 4.68 / 50 |
| Evidence points | 19.10 / 30 |
| Synthesis points | 0 / 12 |
| UX points | 0.80 / 8 |
| Organizer-checked claims | 14 correct; 8 wrong company; 22 checked |
| Checked-claim accuracy | 63.64% |

The [live board](https://builderr.ai/challenges/signalpost), checked 14 November, confirms this result and says qualification requires 65 points and at least 95% of checked claims right. The leader is at 69.27; no entry currently qualifies. These are directional results from a 500-company round. The user-provided organizer email requires the repository, branch and exact replacement commit **by 15 November, 09:00 IST**. Use this earlier, entry-specific deadline rather than the generic 16 November closing date.

The [evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md) measures attribution, evidence, external coverage, explanations and execution. Valid JSON, large registry claim counts and test success cannot substitute for exact-company accuracy. The remaining six wrong-company cases were not provided; this diagnosis cannot claim to have reproduced all eight.

## 2. Work actually performed

- Inspected website identity, social attribution, article and vacancy extraction, official-data handling, evidence retention, refresh, synthesis, request scheduling, console/showcase rendering, CI and publication workflow.
- Ran all Python tests and diagnostic regressions: **289 passed in 83.54 seconds**. This includes seven untracked JBOX export tests already in the workspace; the collector is still the committed implementation.
- Ran frontend resilience checks: **16 passed**. These are code-level checks, not a new mobile/browser visual audit.
- Ran both organizer-named companies live: **2 valid envelopes, 32 requests, 19.1 seconds, $0 declared external API cost**.
- Audited those two live outputs: all 215 evidence records passed artifact checks, including 97 account claims and 30 filing-history claims. **That audit passed even though the OTIS attribution was wrong**, directly demonstrating the semantic gap.
- Added an offline adversarial reproducer, `eval/organizer_attribution_probes.py`, covering foreign-region identity, global-parent identity, a legal-name control, social handles and an ownership-conflict refresh.
- Completed a fresh 1,100-company live baseline under a 2,000-request ceiling; final measurements appear below. The input is an existing development cohort, not a blinded holdout or the organizer's private 500-company batch.
- Re-audited retained artifacts from the earlier breadth run: 75,564 evidence records, no missing references or invalid objects/locators, and 48,707 account claims matched their retained sources. This is a historical artifact-integrity result, not a fresh accuracy result.

Raw diagnostic outputs are local under `out-organizer-diagnosis/` and intentionally ignored by Git. The [JSON summary](organizer-diagnosis-20261114.json) preserves aggregate findings, run metadata, artifact hashes and probe results. No production fixes, commit, push, external message or JBOX deployment were performed as part of this diagnosis.

## 3. Confirmed release blockers

### D1 — OTIS AS is still assigned an Indian regional website (P0)

**Target:** OTIS AS, organisation number `919419105`.

The live pipeline accepted `https://www.otis.com/en/in/`. Its identity evidence was the title `Lift Manufacturing Company, Elevators & Escalators | Otis India`. The resulting description explicitly describes operations in India. This does not establish ownership by the Norwegian legal entity OTIS AS.

The recorded acceptance reason was that the registered email domain matches the website and the legal name appears in identity fields. The latter assertion is too strong: `exact_name_present()` removes legal-form tokens, reducing `OTIS AS` to `otis`. Its finite qualifier list rejects some parent labels but not `India` or `Worldwide`. Shared corporate email domains cannot repair this missing legal-entity proof.

**Affected code:** `src/signalpost/web.py`, especially `name_tokens`, `exact_name_present`, `Page.identity_quote`, `visit_site` and downstream publication. Same-domain regional redirects retain the shared-domain appearance, so cross-domain safeguards do not catch this.

**Offline reproduction:** both the Otis India and Otis Worldwide title fixtures are unexpectedly accepted; the OTIS AS legal-name control is also accepted. The live failure is stronger evidence than a hypothetical matcher concern.

**Required correction:** preserve legal identity and attach an explicit verified entity scope to each accepted page/path. A shared brand/domain/email is a discovery hint. Require the target org number or an unambiguous full legal name in a relevant ownership context, with conflicts taking precedence. Do not fix this with a growing blacklist of country names. Re-check descriptions, contacts, social links, jobs and news against the verified scope rather than inheriting trust for an entire corporate domain.

### D2 — Refresh preserves rejected ownership and the index republishes it (P0)

A synthetic previous profile contains `gbbl.no` as the cooperative's official website. A new profile has no website claim and records an ambiguous identity result because the site presents a different organisation number. `refresh.diff()` nevertheless copies the prior website into current claims, adds `stale_since` and marks it `available`. The showcase index still returns that URL as its official website.

**Affected code:** `src/signalpost/refresh.py` (`UNREADABLE`, carry-forward branch); `src/signalpost/showcase/build.py` (`_published`, `_index_row`). The generic benchmark also includes stale available claims, unlike `eval/metrics.py`. Synthesis already excludes stale claims; that protection is not shared by all consumers.

This is a controlled lifecycle reproduction, not an assertion that this exact old cooperative row exists in the committed sample. It proves a real failure mode when a previously wrong claim is refreshed.

**Required correction:** distinguish temporary inability to fetch from affirmative identity conflict. Invalidate ownership-conflicting claims and all dependent external claims; retain history separately. Ordinary transient failures may preserve explicitly stale history, but stale or revoked claims must not appear as current official links or contribute to current coverage. Add a structured rejection reason and provenance dependencies instead of matching prose reason strings.

### D3 — Social handles can still collapse shared brands (P1; ownership risk)

The organizer's exact `youtube.com/user/OtisElevatorCompany` example is now rejected by the offline gate. This is a meaningful existing fix. However, the shared-brand URL `youtube.com/user/otis` passes the same gate on a parent-branded page fixture. We have not independently established the actual owner of that second account, so it is a risk probe, not a newly proven wrong-account publication.

**Required correction:** a matching short brand handle is insufficient for a subsidiary. Carry exact-entity scope into social extraction; when a domain is shared, require explicit subsidiary attribution and permitted supporting evidence. Record parent/group accounts as labelled relationships, or abstain, rather than publishing them as the company's own accounts.

### D4 — Contact and careers landing pages are published as company news (P0)

The completed 1,100-company run emitted exactly two `company_news` claims, both for DIAKONHJEMMET OMSORG AS (`920008259`):

- [Kontakt oss](https://www.diakonhjemmetomsorg.no/kontakt-oss), a contact directory, dated by the extractor as 16 December 2024.
- [Ledige stillinger](https://www.diakonhjemmetomsorg.no/kontakt-oss/ledige-stillinger), a careers landing page linking to job portals and related organisations, also dated as 16 December 2024.

Inspection of both source pages confirms they are not news posts. Their `article:published_time` metadata is a page publication timestamp; it does not establish an article. These are wrong-type claims, separate from wrong-company attribution. Both retained-evidence audits still pass because the timestamps and headings really exist.

**Root cause:** `_news.from_page()` accepts explicit article publication metadata with a heading, while `single_item_url(..., "news")` excludes a limited set of news-index endings. It does not require a substantive article or reject Norwegian contact/careers page types. `add()` excludes some English job paths but misses these cases. An offline fixture now reproduces both false publications.

**Required correction:** classify the page before interpreting its date. Require an article body and positive post context, reject utility/contact/careers/list/search pages across supported languages, and retain the date only after that decision. Support both structured and visible posts; do not accept a CMS's generic `Article` or publication metadata as sufficient by itself. Add positive article controls so the fix does not simply eliminate news coverage.

## 4. Organizer examples: fixed versus still failing

| Case | Current observation | Conclusion |
|---|---|---|
| VESTSIDEN HAGEBY IV BORETTSLAG, `888078622` | Candidate redirects from `skien.bbl.no` to `gbbl.no`; site presents org `947173219`; rejected | Named manager-domain problem is prevented in a clean live baseline |
| OTIS AS, `919419105` | `otis.com/en/in/` and India description published | Current code remains unsafe to resubmit |
| Exact global YouTube URL from email | Rejected by offline social probe | Specific handle regression is fixed; this is not blanket social precision proof |
| Previously wrong website followed by ownership conflict | Old claim carried as stale; showcase index exposes it | Refresh/UI can undo the practical benefit of rejection |

## 5. Coverage diagnosis: why news and jobs remain weak

### Discovery and budget allocation

`pipeline._plan()` reserves substantial requests for exact-key official data. Large batches require roughly one annual-account request per company before website robots checks, redirects, proof pages or articles. The web budget is split 85% discovery and 15% enrichment. The tail pass gives official families priority. Thousands of additional accounting facts therefore coexist with very little external discovery.

The current default is `legacy`; the breadth strategy remains opt-in. Earlier breadth measurements found 38 website companies instead of 29 in a historical baseline. That does not prove improved recall or precision, and promoting breadth would not fix D1.

### Jobs

- NAV requires a deployment-approved token; this environment's feed is unavailable. A blocked source is not evidence that a company has no vacancies.
- Company-site discovery fetches at most two job-related pages and restricts candidates to the same registrable domain. Common external ATS links are excluded.
- `_site_jobs()` requires JSON-LD `JobPosting`, a single detail URL, valid publication date, exact hiring organisation, and expiry or a recent direct-apply condition. Plain HTML ads and supported but unimplemented ATS formats are missed.
- Those identity and date checks should remain strict. Add permitted ATS adapters and visible-HTML extraction only with exact employer and detail-page evidence. A careers landing page, search URL or parent vacancy is still not an acceptable fallback.

### News

- News extraction depends on accepted websites, a small enrichment allowance, bounded sitemap/list traversal and detail-page date evidence.
- Company-specific publisher checks are useful but need to support legitimate graph/HTML variants without accepting group-wide material. Publisher-reference resolution already exists.
- `registry_event` and `company_news` share the activity family. An available activity family can therefore conceal zero company news. Dashboards must report these fields separately.
- Modified timestamps, feed update timestamps and sitemap lastmod must remain discovery metadata, not publication dates. Add a diagnosed rejection reason for each article candidate so discovery misses and publication rejections are distinguishable.

## 6. Evidence, financials, synthesis, frontend and operations

| Area | Observation | Impact / next action |
|---|---|---|
| Official financials | Existing tests and retained-source audits exercise account scope, units, dates and locators | Preserve these protections; this session has not found a new fabricated financial value |
| Website evidence | A perfectly retained Otis India title can support the wrong legal entity | Add semantic ownership adjudication; hashes and spans are necessary but insufficient |
| Confidence | Website confidence is a heuristic 0.9 or 1.0 | Do not present this as calibrated correctness probability |
| Synthesis | Current deterministic brief code exists and filters stale claims | Old official 0/12 does not prove the current feature is absent; current wrong descriptions can still contaminate summaries |
| Frontend | 16 resilience tests pass, but stale official links survive in index data | Test semantic publication rules across search, profile, compare and evidence views |
| Pages deployment | Workflow builds `reports/run-1000-envelopes.jsonl.gz` | Updating extraction code does not refresh the public data; regenerate an audited sample and bind it to a commit/run manifest |
| CI | Python tests, five-company live smoke and snapshot audit exist | Add frontend checks, ownership regressions, lifecycle checks and a reviewed external-claim gate |
| Request safety | Redirects and public-address policy are checked; robots and bounded reads exist | DNS is checked before the HTTP client resolves/connects; connection-time address pinning remains a hardening item, not a reproduced exploit |
| Console | Loopback bind, Host/Origin checks and fixed action commands exist | No new arbitrary-command issue reproduced; this is not a penetration-test certification |
| Environment | No LLM or paid search provider configured; NAV token optional | Declare missing access honestly; do not solve coverage with an undeclared/restricted crawler |
| Submission | Organizer ran an older frozen commit | Freeze tested code, report full hash and branch, obtain acknowledgement; do not describe an unsubmitted local fix as scored |

The committed public sample identifies itself as `run-1000-rev18b`: 1,000 profiles, three website claims, four company-news claims and zero job claims. Neither disclosed organizer example appears in that sample. These are publication counts, not independently verified facts, and the sample is not the organizer's scored batch.

The fresh scale run also encountered a real bulk-source transport failure: the roles archive connection closed after 7,114,441 of an expected 129,976,925 bytes. `bulk._download()` allows an up-to-eight-minute deadline and retries; the pipeline then falls back to per-company sources. The source outage is external, but waiting for large archives and relying on costly fallback is a design risk under strict time/request limits. Add per-source time reservations and test partial archives, slow streams and unavailable bulk sources. A readable envelope after degraded enrichment is completion, not full coverage.

## 7. Metrics that can and cannot be stated

- **Official checked-claim accuracy for eaef804: 14/22 = 63.64%.** This is a small checked sample, not a population estimate and not a current-code score.
- **Current independent precision, recall and F1: unknown.** The current live OTIS failure proves a nonzero wrong-company risk; 289 passing tests do not support a 95% accuracy claim.
- **Current coverage:** measure companies with current supported candidate publications and distinguish news from registry activity. These counts are availability, not recall against a checked reference collection.
- **Current official score/rank/top-three likelihood: not defensibly predictable.** The known attribution blocker already prevents a readiness recommendation.
- An accuracy sample must audit external claims directly. Allowing thousands of easy registry facts to dominate the denominator would conceal the exact failure the organizer found.
- Build an independent positive reference set for recall; retain missing/blocked/ambiguous cases. A corpus of the agent's own accepted candidates cannot measure missed opportunities.
- Use unlabelled queues as review work, never as truth. Report sample sizes, sampling strategy, unresolved judgements, wrong-company count and uncertainty. A zero-error convenience sample is not proof of population accuracy.

## 8. Reproduction and next action

From the repository root, with dependencies installed:

```powershell
uv run --group dev pytest tests eval/diagnostics -q
node --test eval/ui_resilience_check.cjs
uv run python eval/organizer_attribution_probes.py
uv run signalpost run --organisations out-organizer-diagnosis/named-cases.jsonl --out out-recheck-named --workers 2 --job-days 7 --max-requests 150 --max-minutes 5 --max-cost 0 --no-showcase
uv run signalpost run --organisations eval/rankup/scale-1100.jsonl --out out-recheck-scale --website-strategy legacy --bulk-files --workers 8 --job-days 7 --max-requests 2000 --max-minutes 15 --max-cost 0 --no-showcase
uv run python eval/snapshot_audit.py out-recheck-scale --output out-recheck-scale/source-audit.json
uv run python eval/metrics.py out-recheck-scale --output out-recheck-scale/metrics.json
```

The named-case input consists of two JSONL rows with `organisation_number` equal to `888078622` and `919419105`. No credentials are required for these reproductions. `$0` refers to declared external API charges, excluding compute, bandwidth and development-tool costs.

Implement the ordered [recovery plan](../docs/dev/organizer-recovery-plan.md). Fix attribution and revocation first; then run a small live canary before repeating broad discovery. Ask the organizer for the remaining checked-claim records and their evidence so every reported mismatch can become a regression. Do not assert that all eight errors are fixed based on the two disclosed examples.

## 9. Completed fresh scale baseline

Run `run-20261114T052156Z`, source HEAD `11eee14`, legacy strategy, live registry (no supplied frozen snapshot), 14 November 2026. The 15-minute local limit is stricter than the earlier 45-minute development allowance; this run finished within both. The same 1,100-company development input was used in earlier experiments, so differences are not a controlled A/B result.

| Measurement | Observed |
|---|---:|
| Valid terminal envelopes | 1,100 / 1,100 |
| Requests | 1,920 / 2,000 |
| Elapsed | 612.2 seconds (10.2 minutes) |
| Declared external API cost | $0 |
| Companies with identity | 1,097 |
| Companies with financials | 1,090 |
| Companies with leadership / locations | 100 / 93 |
| Companies with published websites | 23 (2.09% of inputs) |
| Companies with social claims | 11 (13 claims) |
| Companies with descriptions | 14 |
| News publications | 2, both confirmed non-news utility pages; zero valid news among published items |
| Job publications | 0 |
| Registry events | 4,264 across 1,096 companies |
| Website attempts / completed checks | 74 / 71 |
| Website budget-unattempted companies | 1,023 |
| Leadership / locations failed states | 997 / 997 |
| Evidence records audited | 71,285 |
| Account claims verified against retained source | 48,707 |
| Missing references / invalid objects / invalid locators | 0 / 0 / 0 |

The two news items were explicitly inspected; **0/2 are valid news posts**. This narrow finding is not overall model precision and says nothing about how many genuine posts were missed. Website and social counts remain unadjudicated availability counts. The review exporter produced **227 unlabelled review tasks**, including every published website, social and news claim. No automatic "supported" labels were generated.

Reported per-company worker p50/p95 are 16/5,030 ms. These exclude the practical effect of long shared bulk-source waits and are dominated by companies that immediately hit phase limits; the 612.2-second end-to-end runtime is the meaningful batch latency. An apparently fast median is not successful research completion.

The source audit verifies retained locators, not every real-world fact. Three inputs lacked current registry identity; financial and enrichment failures are explicit. The run's true value as a diagnostic is that it completed within limits while exposing both semantic false positives and severe coverage loss. Do not label it a passing accuracy benchmark.
