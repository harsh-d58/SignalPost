# SignalPost technical plan for the November revision

**Superseded for remaining work on 11 November:** use the [inspected metrics improvement plan](metrics-improvement-plan.md), which separates completed protections from the remaining request-allocation, discovery and independent-evaluation work. The plan below records the earlier implementation sequence.

**Implementation update, 10 November:** see [measured results and remaining work](../../reports/rankup-implementation.md). The source-contract changes, retained-evidence audits, bulk/direct comparison, refresh checks and smoke/scale runs are implemented. On the same 1,100-company cohort, bulk improved leadership by 87.73 percentage points and workplaces by 66.73 points at 1,920 requests, with 60/60 direct-source parity checks after address normalization. Use the documented bulk flag for large batches. The 77-point score remains a target; external discovery coverage and independent recall labeling remain open work.

**Prove the evidence and refresh contract, then run bulk registry as the first challenger.** The revised default run used 1,920 requests on 1,000 companies, including 996 annual-account requests and 339 individual role and workplace requests. It returned 1,000 valid envelopes in 91.5 seconds at $0, but covered roles for only 175 companies and workplaces for 142. Consolidating those lookups could recover both families and free requests for verified websites, news, and vacancies. [Local run report](../../reports/revision-scale-1000-run-report.json)

## What governs the revision

| Input | How it governs this plan |
|---|---|
| Participant brief and evaluation contract | Define the scoring, eligibility, submitted artifacts, official inputs, envelope and refresh requirements. The supplied version 2 contract governs the revision. |
| Source policy and the four publication rules | Define what can be collected, retained and published. Apply them to every connector and every claim. |
| Agent playbook and learning harness | Provide architecture and experiment guidance. Reuse the existing Python crawler, schemas and evaluation scripts. Adopt a suggested tool or strategy only after a measured improvement. |
| Frozen 2025 filer universe | Provides a sampling frame for local evaluation. It includes names, registry fields and website candidates. Builderr supplies the official batch, frozen registry identity snapshot, evidence cutoff and resource limits separately. |

The supplied gzip has **411,160 unique organisation numbers**. Both digests match the brief. Keep this file outside the release payload, record the digest and sampling seed with each local cohort, and use its website values only for discovery or host grouping. The archive is separate from the evaluator's official identity snapshot and proves no current web claim.

| Verified SHA-256 | Digest |
|---|---|
| Download archive | `1c89710e5b01f8617e86d09fbdff4a52f2f8dbbba297e74f7164b5984f5a0384` |
| Decompressed JSONL | `b82d6a3e7231d1759a958c282bc4366b80ec2fab8095053d8ed7fa9cd01bc838` |

## Score to beat

As checked November 9, the public board still shows the October 17 review on 300 companies. Karthik leads provisionally with **70.43**, ahead of Hardik at **61.75** and Venkat at **59.76**. Karthik's breakdown is 35.77 recall, 27.46 precision/evidence, 7.20 synthesis and 0 UX. The board excludes unavailable review, rating and sentiment evidence from that round and scales its recall result. The row labeled Harsh has no verified association with this repository. [Public standings](https://builderr.ai/challenges/signalpost)

The current rubric gives 50 points for recall and coverage, 30 for precision and evidence, 12 for synthesis, and 8 for UX. Within a field family, recall weights companies found at 70% and distinct verified facts at 30%. Qualification requires 65 overall and a valid official run. A material wrong-company match or fabricated financial value prevents qualification. Builderr scores fresh batches that may reach 1,100 companies and averages scheduled results. Revisions apply prospectively. The page lists November 16 as the cutoff and allows up to four revisions after the initial submission. [Scoring](https://builderr.ai/challenges/signalpost#scoring) · [Evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md)

Use **77/100** as a planning target: 32 recall, 29 precision/evidence, 10 synthesis and 6 UX. With the other three dimensions at those targets, 25.44 recall would exceed the posted 70.43. At 29 evidence, 7.2 synthesis and 0 UX, the same comparison requires 34.24 recall. This arithmetic shows the value of delivering reviewable synthesis and UX alongside recall gains. Builderr's reference collection is unavailable locally, so these figures are targets and sensitivity checks.

## 1. Close the contract gaps before increasing coverage

**Owners in code:** `pipeline.py`, `model.py`, `http.py`, `refresh.py`, `cli.py`, `eval/verify_evidence.py`, `eval/refresh_replay.py`.

- **Official entry point.** Take the supplied organisation-number file, registry identity snapshot, cutoff and limits through one documented command. Adapt the existing `--bulk` path to the evaluator's snapshot format and test which snapshot fields anchor identity when live records differ. Record the supplied snapshot hash, policy and cutoff in the run manifest. Declare any external caches and apply the same cutoff to evidence eligibility. Keep credentials in documented environment variables and out of artifacts.
- **Terminal envelope.** Validate identity and public brand, accounts and available history, leadership and workplaces, official website and company profiles, hiring and dated activity, evidence and availability, and refresh metadata with material changes. Include snapshot references and errors. Verify one envelope per supplied organisation number in the evaluator format, even with unavailable or blocked sources. Exercise all six states and the distinction between missing data and a filed zero.
- **Durable evidence.** The current `Snapshot` carries fetch metadata in memory and `Evidence` serializes an excerpt and digest. Add a content-addressed snapshot store and serializable references. Capture requested and final URL, redirects, status, retrieval time, content digest, source class, access policy and parser version before extraction. Keep claim locators such as a JSON path, DOM selector, text span, table cell or PDF page. Verify that the locator supports the actual company and value, including currency and period. Retain raw content only where source terms and privacy allow it. Apply source-specific expiry and restrict public artifacts to permitted excerpts and references. If evidence cannot be retained and verified as required, keep the claim unpublished.
- **Refresh replay.** Diff stable claim keys across immutable snapshots. Record current and prior supported values, first and last observation, typed material changes and evidence on both sides. Replay an identical snapshot twice and assert stable IDs, no duplicates and zero false changes. Replay source failure, blocked fetch, truncated feed, actual ad withdrawal, new filing and role change. Preserve supported prior values as stale after failed refreshes and apply source retention rules to withdrawn jobs. Vary recheck cadence by volatility. Keep this path separate from strategy selection.

**Release gate:** The evaluator command works from a clean checkout with the pinned lockfile. Every envelope validates, every material claim resolves to reproducible evidence, refresh passes replay, and the batch exits within supplied limits even under partial source failures. Run a deliberately constrained case to check that a populated output file cannot hide a missed deadline or a failed write.

## 2. Turn the request ceiling into a source allocation problem

**Owners in code:** `pipeline.py`, `bulk.py`, `registry.py`, `http.py`, `budget.py`.

- Test `--bulk-files` against the documented Brønnøysund role inventory and workplace CSV. Stream and filter on official organization numbers. Record source URL, retrieval date, snapshot digest and row-level provenance. Compare against direct lookups on 30 companies with and without role or subunit records. Benchmark transfer time, compressed bytes, disk use, peak memory, missing rows and parity. [Brønnøysund open data](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html)
- Start bulk downloads alongside identity and accounts. Set download and parsing deadlines, check completion before treating a missing row as absence, and fall back to direct lookups with a fixed quota if the stream fails. Resolve roles to the exact entity and workplaces to the registered parent. Keep direct mode as the benchmark and fallback.
- Reuse successful same-run snapshots by exact URL and request context. Keep robots rules by origin and exclude authentication material from cache keys and logs. Measure requests from robots, redirects, failures and retries. Allow unused request capacity to flow between phases without overrunning the hard cap.
- Spend discovery requests first on companies with a registry URL, corporate email domain, or exact-ID Wikidata website. Allow one useful source per company before going deeper on a company already covered. Track newly verified company-family pairs and distinct facts per 100 requests. Compare allocations on the same inputs and review precision before accepting a higher-yield route.

Initial 1,100-company request budget for the bulk experiment. These are local ceilings, including retries and redirects, with 80 additional requests reserved inside the 2,000-request local cap. Use the organizer's supplied limits for official runs.

| Work | Planned ceiling |
|---|---:|
| Annual accounts | 1,155 |
| Shared registry, bulk snapshots, activity and candidate indexes | 65 |
| Vacancy feed and ad verification, subject to permitted access | 65 |
| Group records and targeted additional official sources | 80 |
| Website verification, news and careers | 430 |
| Fallback and redistribution | 125 |
| **Total planned** | **1,920** |

**Proposed promotion floor:** Improve available role and workplace coverage by at least 10 percentage points each on the same scale batch, with matching direct-lookup records in the audit and no loss of verified external coverage. Predeclare this floor before validation. If bulk delivery is unreliable, keep direct mode and evaluate request redistribution separately.

## 3. Improve recall behind the four publication gates

Use an explicit source ladder. Start with official records and filed accounts, then verified company-owned pages, then official or licensed APIs and permitted public pages. Search, Wikidata, public brand names and leadership bridges can suggest candidates. Re-fetch the underlying permitted source and require reverse proof to the anchored entity. Label each parent, subsidiary, group, franchise and brand relationship separately. Keep candidate ranking outside the publication gate.

| Family | Discovery experiment | Publication gate |
|---|---|---|
| Official site | Rank registry URLs, corporate domains and exact-ID candidates. Check `/kontakt`, `/om-oss` or legal notices for a promising candidate. | Establish ownership with the exact org number in ownership context or the full legal name plus independent registry corroboration. A shared group domain must resolve to an exact entity page. Conflicting IDs or parent-level branding trigger abstention. Preserve the proven subpath. |
| Social | Inspect verified pages for profile links and structured account references. Validate legitimate trading-name aliases against exact-entity evidence. | Match the actual handle to the legal name or a separately verified alias. Footer placement, `sameAs`, domain similarity and search snippets are candidate signals. Reject vendor, theme, group, share and generic links. |
| News | Use sitemap, RSS and archive pages to discover targets. Fetch individual posts and prefer the primary article over its listing card. | Require an article URL, substantive headline, explicit publication date and company attribution. Reject menu labels, product pages, future dates and modification-only timestamps. Validate the publisher on group domains and deduplicate canonical URLs. |
| Jobs | Compare 7- and 30-day NAV lookback when access is permitted. Follow individual ad links from verified employer career pages or permitted ATS sources. | Require a distinct ad ID or canonical detail URL, current status and exact legal employer or registry-proven workplace. Reject group vacancies, searches, landing pages and expired ads. |

For NAV, treat the public token as experimental. Confirm its permitted scope for the official run and any public showcase. Use the approved evaluator credential if needed. Refresh status by ad ID, remove inactive ads from public display and preserve only retention-safe change evidence. If access is unavailable, use company-owned ad pages and mark the NAV lane blocked. [NAV feed documentation](https://navikt.github.io/pam-stilling-feed/)

Maintain a connector decision table with allowed endpoints and access method, terms or licence, allowed evidence and retention, credentials, request limits and blocked behavior. Honor robots and access restrictions at fetch and redirect time. A public token, public link or open-source client does not establish permitted access. Unofficial clients may only enter a private candidate-discovery experiment where the collection itself is permitted. A connector used for scoring must be declared, have a permitted access basis and independently verify claims from durable permitted evidence. Company copy can support a sourced description. Independent sentiment requires an independent permitted source.

Use static HTML and structured data first, then DOM and text extraction. Try browser rendering only for a detected JavaScript shell after measuring its added verified coverage and resource cost. For official filing PDFs start with text extraction, then test layout or OCR for the remaining failures. A model can suggest candidates or summarize validated claims. Exact identity and publication decisions stay with deterministic checks. Prefer first verified claims across companies before fetching more posts from a covered company. Leave additional review and sentiment integrations behind a separate source-rights and coverage experiment.

## 4. Run a versioned evaluation loop

1. **Freeze the cohorts.** Sample from the verified universe using a recorded seed. Use a representative development sample plus a separately reported hand-labeled trap set. Freeze an independent 100-company validation cohort and keep an untouched 100-company release smoke cohort and 1,100-company scale holdout. Split by organisation number and known registrable host or group. Audit newly discovered host overlaps and exclude contaminated rows from blind comparisons. Existing audit batches have been inspected and can serve as baselines or development data. Run same-input baseline/challenger tests during development and lock thresholds before the final holdout.
2. **Register each experiment.** Give each route an ID and version. Begin with `registry_direct`, `registry_bulk`, `registry_site`, `sitemap_static`, and `job_detail`. Record routing conditions, source policy, thresholds, budget and rollback version. Extend the existing `eval/` tooling with a single comparison command that replays saved evidence for correctness and runs live for cost and reachability.
3. **Save attempts and score.** Record company ID, strategy version, requested and final URLs, redirects, snapshot references, all candidates, decisions and reasons, identity proof, states and errors, requests, time and cost. Hand-label exact attribution, evidence support and expected availability. Report per-family precision, recall, coverage and abstentions, crawl completion, evidence-span validity, refresh accuracy and false-change rate, cost per company and p50/p95 runtime. Score local recall by `0.70 × company recall + 0.30 × distinct-fact recall` against the labeled pool. Keep local pool versions and use the contract's sparse-pool treatment when reference opportunities are insufficient. A re-fetch check measures excerpt availability. Manual review tests whether the excerpt proves the claim.
4. **Promote or roll back.** Require zero new material wrong-company publications or fabricated values, no precision regression in audited strata, complete and verifiable material evidence, the declared coverage gain, idempotent refresh and compliance with time, request and cost limits. For a web challenger, start with a proposed floor of five additional verified company-family pairs per 100 labeled companies at the same request cap. Record the report and decision, including rejected challengers. Freeze code, lockfile, strategy routing, models or prompts if used, thresholds, publication gates, source allowlist and budgets before the official batch. Refresh can gather new evidence under that frozen policy. Keep official results and hidden labels out of strategy tuning.

## 5. Make synthesis and UX easy to score

- Generate a short brief with three explicit parts: what the company does, the most useful verified change, and what remains unknown. Cite claim IDs for every material sentence. Explain the account period and currency before comparing figures. Link changes to before-and-after evidence and separate active, stale and unavailable facts.
- Give reviewers three direct flows in the generated showcase: find by org number or name, compare two companies, and open the exact source from a claim. Run them at desktop and mobile widths and with keyboard-only input. Add the showcase URL and one sample profile route to the submission so judges can reach the evaluated features in one click.

## 6. Sequence the release

| Dates in IST | Work | Evidence to retain |
|---|---|---|
| Nov 9–10 | Freeze the baseline and cohorts. Implement the snapshot references and evaluator contract checks. Test bulk provenance, parity and failure fallback on development inputs. | Evidence and refresh replays, labeled traps and same-input bulk A/B reports. |
| Nov 11–12 | Implement request redistribution and measure the highest-yield website, article and job discovery challengers. Lock promotion thresholds before validation. | Versioned attempts, per-family metrics, source decisions and a rollback configuration. |
| Nov 13–14 | Validate the chosen routes, review synthesis and test desktop/mobile workflows. Freeze the candidate and run the untouched smoke and scale holdouts. Inject malformed responses, timeouts, rate limits and bulk outages on a separate fault suite. | Complete envelopes, verified evidence, zero known material attribution or financial fabrication errors, zero false changes on identical replay, and requests, time and cost. |
| Nov 15 | Validate the frozen SHA from a clean checkout with the single evaluator command. Confirm remaining revision slots and prepare the release materials. | Repository URL, exact commit SHA, public 100-company smoke report, one command, model/API/licence declarations, cost, agent name, contact and showcase link. Allow a day before the November 16 cutoff. |

Local validation uses 2,000 outbound requests, 45 minutes and $10, with an internal target of at most 1,920 requests, under 15 minutes and $0 for the current source set. The official evaluator supplies its own limits. Submit the public 100-company report with the revision. Keep the 1,100-company run and precomputed profiles as local engineering evidence. If a challenger misses a gate, freeze the strongest configuration that passes and keep the failed experiment for later development.
