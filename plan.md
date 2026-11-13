# SignalPost: plan to outperform the current leader

Date: 12 November 2026. Status: proposed implementation programme, grounded in completed local tests. This document does not claim that the proposed changes are implemented or that a competition score has been measured.

## 1. Objective and decision rules

Build an agent that consistently finds more independently supported, exact-company information on unseen Norwegian entities, returns complete results within the supplied resource budget, and makes those results easy to understand and verify.

Use **82/100 as an engineering target**, not a forecast or guaranteed winning score. The live leaderboard currently displays Karthik at 70.43, with recall 35.77/50, evidence 27.46/30, synthesis 7.20/12 and UX 0/8. Those are directional, provisional results from a 300-company round; the reference collection and competitors can change. Do not associate the leaderboard's “Harsh” entry with this repository without verification.

| Dimension | Planning target | What must improve |
|---|---:|---|
| Recall and coverage | 37/50 | More supported company–field opportunities, especially external facts |
| Precision and evidence | 29/30 | Exact legal attribution, valid dates, reproducible source support |
| Synthesis | 10/12 | Useful cited explanations, changes and explicit unknowns |
| UX | 6/8 | Find, compare and verify profiles on desktop and mobile |
| Total | 82/100 | A reliable combined product, not merely more extracted records |

Arithmetic only: with 29 evidence, 10 synthesis and 6 UX, recall would need to exceed 25.43 to exceed the posted 70.43. That is not a reason to reduce the recall target; other entrants and scoring pools can improve.

Source of current rules: [challenge and leaderboard](https://builderr.ai/challenges/signalpost#scoring), [evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md), checked in this conversation on 12 November 2026.

The current rubric is 50/30/12/8, superseding the earlier 35/30/20/10/5 description. Within each external family, coverage is 70% company recall and 30% individual-fact recall. Do not invent unpublished family weights. Qualification requires an official valid run and at least 65 overall; a material wrong-company publication or fabricated financial value prevents an official qualifying result. Scores are averaged across scheduled batches for active versions, so reliability and prompt release of verified improvements matter. Revisions do not replace earlier results.

The published contract allows the initial version plus four revisions through 16 November 2026. Confirm remaining revision slots from actual submission acknowledgments before release; do not infer them from local commits. Use the evaluator's actual supplied limits. The local stress budget in this plan is 2,000 requests, 45 minutes and $10 external API cost; this does not override future evaluator settings.

## 2. Baseline: measured strengths and weaknesses

### Latest fresh 100-company website pilot

See [pilot report](reports/website-pilot-20261112.md) and [machine-readable results](reports/website-pilot-20261112.json).

| Observation | Result | Interpretation |
|---|---:|---|
| Valid terminal profiles | 100/100 | Output contract passed on this cohort |
| Requests / runtime / declared API cost | 1,137 / 239.6 seconds / $0 | Fits the local smoke budget |
| Published websites | 23 companies | Availability, not recall |
| Website ambiguous | 48 companies | Requires adjudication before changing gates |
| Website blocked / not available | 10 / 19 | Access and discovery failures must remain distinct |
| Social profiles | 9 companies | Ownership precision still needs independent review |
| Company descriptions / contacts | 13 / 55 | Potential synthesis inputs, with source constraints |
| Jobs | Blocked for all 100 | NAV access absent; no job-quality conclusion possible |
| Evidence audit | 8,790 entries; no invalid references/objects/locators | Source integrity, not independent factual precision |
| Python regressions | 275 unique tests passed | Existing behavior protected, not a live accuracy estimate |

The cohort contains 20 random entities, 40 provisional positive candidates and 40 ownership challenges. It excludes 3,722 previously tested entities. It is a development cohort, not a representative pooled accuracy sample. All ownership labels remain pending. The normal pipeline published websites for all 20 probe-accepted companies plus three others. Candidate injection therefore showed no recovery gain in that experiment.

The diagnostic split is 23 published websites, 61 unresolved candidate cases and 16 companies with neither a probe candidate nor a published baseline website. These categories are disjoint; the 48 ambiguous cases are not an additional cohort to add to them.

### Scale bottleneck

The earlier 1,100-company release run produced 1,100 valid outputs using 1,920 requests in 429.3 seconds, but published only 29 websites. Its website states included 968 failures attributed to website-phase budget exhaustion. This run preceded the last publisher-reference fix; do not present its results as a final-code benchmark. See [release report](reports/release-readiness-20261112.md).

At 2,000 requests for 1,100 companies, fewer than two outbound requests per company are available on average before retries and other sources. A strategy requiring several independent requests per company cannot cover the whole batch. Better scheduling, shared fetches and permitted bulk sources are essential; concurrency alone does not solve this constraint.

### Existing capabilities to extend

- `src/signalpost/synthesis.py`: deterministic, claim-cited briefs already exist.
- `pipeline.py`, `budget.py`, `bulk.py`, `registry.py`: batching, phase budgets and deferred enrichment already exist.
- `web.py`: website identity gates, news and company-site extraction already exist.
- `http.py`, `evidence.py`: fetch controls, caching and retained evidence already exist.
- `refresh.py`: material changes and evidence-preserving refresh behavior already exist.
- `console/` and `showcase/`: existing frontend surfaces; improve and verify them rather than start over.
- `eval/website_modes.py`: candidate-attribution probe only; extraction-only and independent scored modes remain work.

## 3. Work sequence and dependencies

| Phase | Priority | Dependency | Deliverable / exit gate |
|---|---|---|---|
| A. Ground truth and instrumentation | P0 | Existing pilot | Reviewed labels, explicit denominators, stage failure report |
| B. Batch allocation | P0 | Baseline counters; A for outcome scoring | Same-budget scale comparison with more verified opportunities |
| C. Discovery and ownership | P0 | A | Recovered positives without material wrong-company publications |
| D. News, social and jobs | P1 | Verified sites; authorized sources | Independently scored family extraction |
| E. Synthesis | P1 | Supported claims and refresh events | Cited, useful summaries without unsupported inference |
| F. Frontend verification | P1 | E and evidence schema | Desktop/mobile task completion and accessible evidence |
| G. Refresh, security and execution | P0 release gate | Changes from B–F | Replay, transport, clean-install and deadline checks |
| H. Holdout and release | P0 | All applicable gates | Frozen report, exact commit, reproducible command |

Record each change as **observed → reproduced → implemented → regression passed → independently validated → promoted**. Passing a synthetic test does not close a live precision question. Do not implement every proposed experiment in one release: promote only measured gains.

## 4. Phase A — build trustworthy measurements

### A1. Independently adjudicate the pilot

1. Review all 23 published websites and social accounts for the nine companies with published profiles.
2. Review all 61 unresolved candidate cases, including the 40 ownership challenges.
3. Deep-search the 16 remaining discovery gaps independently of the agent's predictions.
4. Establish whether each entity has an accessible, permitted, independently supported website at the cutoff. Do not force a yes/no answer where evidence remains ambiguous.
5. For confirmed sites, record available news, social and job facts so extraction can be measured separately.

A reviewer should inspect original sources and official identity anchors before consulting gate explanations. Review disagreements and every suspected material wrong-company publication separately. Agent predictions must never become reference labels automatically.

Reference record fields: organisation number; legal name; candidate URL; canonical/final URL; relationship type; ownership judgment; source URL; retrieval time; effective date where relevant; evidence span/locator; content hash; access basis; reviewer; adjudication status; label version. Reference facts additionally need family, stable fact key, supported value, publication/reporting date, expiry where relevant and source scope.

Store private review artifacts under ignored output directories. Preserve reviewed versions; do not overwrite answers when generating new tasks. Retain source material only as permitted. The current probe's hashes and observations are not a complete independent reference collection.

### A2. Instrument every failure stage

Use mutually distinguishable reasons: no candidate, invalid candidate, access prohibited, robots denied, network failure, budget not attempted, identity absent, identity conflict, related entity only, extraction empty, unsupported date, wrong employer, duplicate, stale and publication withheld.

For each stage log attempted and eligible companies, requests, elapsed time, cache reuse, accepted facts and rejection reasons. Track final URL, source route and parser version. Separate “did not attempt” from “attempted and found nothing.”

### A3. Metrics definitions

- Exact-company precision: correctly attributed adjudicated publications / adjudicated publications with a resolved judgment. Report unresolved judgments and review coverage alongside it.
- Factual precision: supported, correctly valued and dated claims / resolved reviewed claims.
- Company recall per family: reference-positive companies with at least one correct family claim / reference-positive companies.
- Fact recall per family: matched correct reference facts / eligible reference facts.
- Family coverage proxy: `0.7 × company recall + 0.3 × fact recall`. It is not an official total score without the organizer's weights and pool.
- F1: compute only for the same family and matching unit with measured precision and recall; do not mix company recall with claim precision.
- Wrong-company publications: absolute count and materiality review, not merely an average rate.
- Operational metrics: completion, attempted coverage, budget refusals, blocked rate, requests per newly supported company–family pair, p50/p95 company latency, full-batch runtime and cost.
- Freshness: change-detection correctness, false changes, incorrect removals, stale retention and detection delay where an actual change opportunity exists.

Use confidence intervals with their reviewed sample sizes. Report random, positive and challenge strata separately. No pooled population estimate from the enriched pilot. No numerical precision, recall or competition prediction until the relevant labels exist.

### A4. Expand to the full benchmark

Follow [deep website search plan](docs/dev/deep-website-search-plan.md): 1,000 random entities, 300 independently known-positive cases and 200 adversarial cases, up to 3,000 candidate URLs. The existing 100-company pilot stays development material.

Freeze a development/validation/release allocation before tuning. Group related legal entities and registrable domains into the same split; the public suffix list assists domain grouping but does not prove ownership. Keep unresolved relationships out of the blind split until reviewed. Avoid leakage from historical test sets and manual supplemental discoveries.

Maintain an experiment log with code digest, input hash, reference version, cutoff, cache policy, source policy, config, measured results and rejected hypotheses. If time does not permit review of 1,500 companies, release the honest reviewed subset; do not manufacture a full benchmark from unlabeled crawler outputs.

## 5. Phase B — allocate requests to breadth

Primary files: `src/signalpost/pipeline.py`, `budget.py`, `bulk.py`, `http.py`, `registry.py`.

### B1. Proposed staged execution

1. Validate inputs and load the supplied official identity snapshot or declared permitted bulk source.
2. Collect cheap permitted candidate routes in batches. Deduplicate network work without merging entity identities.
3. Give credible candidates a bounded first verification pass before optional article/job detail enrichment.
4. Extract low-cost supported facts from already fetched pages.
5. Rank follow-up work by estimated probability of a new supported company–family opportunity per marginal request.
6. Reserve time and requests for terminal envelopes, refresh bookkeeping and required remaining sources. Stop optional work before the hard deadline.

Keep a minimum exploration allocation so historical success rates do not permanently starve unfamiliar companies. Do not reward popular companies simply because they have many pages. Every input must receive a terminal state even if no web attempt fits.

### B2. Budget experiments

Start with configurable allocations rather than hard-coded per-company requests. A provisional 2,000-request envelope for experimentation is: 250 registry/bulk/control; 1,000 candidate verification and robots; 250 targeted discovery; 300 external detail extraction; 200 reserve. These are hypotheses, not promised feasibility: instrument existing bulk costs first and revise them before implementation.

All redirects, retries, robots checks, search API calls and shared feed retrievals must count under the declared request policy. Charge parallel operations atomically before dispatch. Reallocate unused optional capacity; never bypass the global cap. Track cache-hit work separately from outbound requests. No hidden prefetch outside the reported run budget.

Share public fetches by safe request identity and declared cache semantics. A fetched group page may be reused, but each company's ownership and each extracted claim must still be evaluated separately. Version cache entries and respect observation cutoff, expiry and refresh requirements.

### B3. Acceptance

Compare baseline and proposed allocation on the same inputs, limits and declared cache state. Use snapshot replay to isolate scheduling behavior, plus separate live runs for network effects. Aim for at least a 10-percentage-point gain in attempted verification among candidate-bearing scale entities and a measurable gain in reviewed company–family coverage. If impossible within the budget, report the limiting request arithmetic and revise the strategy.

Do not promote a change merely because fewer states say “failed”; state relabeling is not recovered information. Complete every input, preserve source support, and introduce zero observed material wrong-company publications.

## 6. Phase C — discovery and exact-entity verification

Primary files: `web.py`, `registry.py`, `wikidata.py`, `http.py`; add a search adapter only after access, cost and evaluator reproducibility are documented.

### C1. Candidate discovery order

1. Official snapshot/registry website and legitimate company email-domain candidates.
2. Official subunit routes, maintaining the parent/subunit relationship.
3. Existing permitted discovery providers such as Wikidata, used only as candidates.
4. Permitted search queries: exact organisation number; exact legal name with municipality; exact name with contact/legal terms.
5. Bounded alternative routes only when earlier candidates fail and marginal value justifies the requests.

Retain query, discovery timestamp, candidate source and rejection history. Search snippets are never claim evidence. The manual Nor-Graphic candidate in the pilot remains outside the frozen baseline until original-source verification and a declared experiment.

### C2. Identity evidence collection

Prioritize homepage identity blocks, contact/about/legal/privacy pages and relevant entity-specific paths. Prefer exact org-number context; distinguish a site operator from customer lists, supplier references, embedded recommendations and agency credits. A printed org number anywhere on a page is not sufficient by itself.

Allow corroborated legal-name identity where consistent with the approved policy; conflicting org numbers or entity names trigger abstention or scoped relationship labeling. Normalize Norwegian characters, punctuation and legal suffixes for comparison without collapsing different legal entities. Treat aliases as evidence-backed relationships, never as unreviewed fuzzy-name permission.

For group domains, determine whether a specific page belongs to the entity and limit extraction to that proven scope. Do not inherit group-wide social accounts, news or vacancies. Cross-host redirects and ATS destinations require fresh scope checks. Preserve parent, subsidiary, franchise and brand relationships explicitly.

### C3. Tests and promotion gate

Test exact subsidiary pages, parent homepages, shared addresses, same-name companies, agency footer links, unrelated org numbers, stale registry domains, domain recycling, redirected brands, international subsidiaries and path escapes.

Target at least +10 percentage points of website recall on independently labeled development positives under equal budgets, or a prespecified missed-opportunity reduction when baseline recall is near ceiling. Review every newly accepted entity. Gains must survive a separate validation split before release.

## 7. Phase D — extract valuable external facts

### News and activity

- Keep registry announcements and company news separately identifiable in metrics.
- Follow bounded sitemap/feed/news-index candidates to actual detail posts.
- Require title, substantive article content, exact-company scope and a supported publication date.
- Keep publication, modification, retrieval and feed-update dates distinct; reject dateModified-only substitutes.
- Preserve JSON-LD graph publisher evidence and reject conflicting/unresolved publishers.
- Deduplicate syndicated/canonical variants without merging distinct dated events.
- Test menus, “see more news,” product pages marked Article, future dates, timezone boundaries, bare graph references and unrelated embedded articles.

### Social profiles

- Extract candidates from verified company scope and normalize profile URLs.
- Reject sharing links, platform homepages, theme/agency accounts and group-only handles.
- Enforce the organizer's company-matching handle requirement. Evidence-backed alias support requires explicit review; it must not become a fuzzy matching shortcut.
- Do not scrape restricted destinations. A company site's permitted link evidence and destination-platform access are separate matters.

### Jobs

- Obtain reproducible authorized NAV access through documented environment configuration before evaluating that source.
- Fetch feeds once per batch and index exact employer identities where permitted.
- Support company-owned and permitted ATS detail ads with exact employer evidence, stable ad identity, publication/expiry dates and active/closed state.
- Reject career landing pages, search results, parent-company vacancy lists and wrong-employer ads.
- Test expiry boundaries, amended ads, explicit closure, partial feeds and temporary source failure. Failure to retrieve a feed must not mass-close previously known jobs.

Acceptance: report company recall, fact recall, exact-company precision and date/status correctness separately for each family. Zero known material wrong-company publications and no unsupported publication dates in the release review. A source with unavailable credentials remains blocked rather than counted as a successful negative.

## 8. Phase E — improve existing cited synthesis

Primary file: `src/signalpost/synthesis.py`; inspect existing behavior and tests before changing it.

Profiles should answer: what does the company do; what is its legal identity and relationship scope; what is the latest supported financial picture; what changed; what remains unknown or inaccessible?

Every factual sentence must resolve to published claim IDs. Exclude stale claims from current-state assertions or label them explicitly. Identify company promotional copy as company-described information, not independent sentiment. Do not infer growth, distress or hiring intent from missing data.

Financial comparisons must use comparable currency, units, account scope and periods. Label group-account fallback prominently. Label derived values and cite all operands. Suppress percentage changes for invalid/zero denominators and avoid misleading comparisons across incompatible reporting periods.

Rank material changes above repeated static facts. Explain an evidence-supported change rather than simply showing raw field differences. Unknowns should distinguish absent, ambiguous, blocked and budget-not-attempted information.

An LLM is optional, not a dependency of this programme. Introduce one only through a paired experiment showing better judged usefulness than deterministic briefs, with strict claim-ID validation, bounded cost, reproducible model details and deterministic fallback. It must not decide unsupported identity matches or invent facts.

Internal review rubric: factual support, clarity, decision usefulness, scope/date correctness and handling of unknowns. Use representative complete, sparse, group-related, changed and blocked profiles. This rubric is a local proxy, not the organizer's unpublished point assignment.

## 9. Phase F — make the product easy to verify

Primary files: `src/signalpost/console/console.html`, `console/server.py`, `showcase/template.html`, `showcase/build.py`. Inspect the existing features first; close actual gaps and preserve working flows. Follow applicable frontend skills when implementation begins.

Required user tasks:

1. Find a company by exact org number or name and identify its legal entity immediately.
2. Distinguish company, group and public brand information.
3. Open a factual claim's source, supporting excerpt and dates in at most two interactions from the profile.
4. Compare two companies using aligned periods and units, with missing values left missing.
5. See material changes with prior/current evidence and observation times.
6. Understand why a family is blocked, ambiguous or unattempted.
7. Complete these tasks on a narrow mobile viewport with keyboard-accessible controls.

Evidence details should show source URL, retrieval time, effective/reporting date, relationship scope and current/stale status. Do not display a classifier score as a verified accuracy probability. Summary cards must lead to the underlying evidence, not dead-end decorative statistics.

Check loading, empty, malformed-data, unavailable-backend, partial-output, long-name and missing-source states. Test keyboard focus, labels, contrast, touch targets and horizontal overflow. Escape all external content and restrict outbound link schemes.

Use existing `eval/ui_resilience_check.cjs`, `ui_check.cjs` and `console_check.cjs` where applicable, plus real browser task checks. Frontend scores cannot be inferred from a successful build or screenshots alone. Supply the required public sample route and documented evaluator access without adding unnecessary authentication.

## 10. Phase G — refresh, transport and execution reliability

Preserve existing idempotent replay and typed-change behavior. Add regression coverage for any changed source adapter, evidence scope or scheduler path.

Required refresh scenarios: identical snapshot; new filing; financial restatement; legal-name/address change; newly discovered website; expired or explicitly closed ad; deleted article; temporary 403/429/timeout; truncated feed; parent-site ownership change. Preserve prior evidence and distinguish stale/unavailable from confirmed removal.

Use controlled replay for specific changes. Live 24/72-hour refreshes are optional experiments only when time permits; unchanged sources provide no positive change-detection opportunity. Do not claim a live refresh result that was only simulated.

Close the documented connection-time DNS rebinding/pinning gap in `http.py` before expanding arbitrary URL discovery. Validate resolved destinations at connection and redirect boundaries, including IPv4/IPv6 private/reserved addresses. Preserve correct Host/TLS behavior. Test redirects to private hosts, changed DNS answers, oversized responses, decompression limits, loops and parser resource limits. Never bypass robots or source access restrictions to improve coverage.

Use global deadline-aware cancellation, atomic output completion and bounded retries. Exercise interruption near the deadline and ensure exactly one terminal envelope per input. Verify exceptions do not leak secrets or destroy partial evidence. Record actual API usage and costs, including failed/retried billable calls.

## 11. Experiment matrix and promotion criteria

| Experiment | Change | Held constant | Primary outcome |
|---|---|---|---|
| E0 | Current baseline | Frozen inputs, config, labels | Reproducible starting measurements |
| E1 | Breadth-oriented budget allocation | Sources and identity gates | Reviewed company–family coverage per request |
| E2 | Targeted legal/contact traversal | Candidate set, budget | Ownership false negatives recovered |
| E3 | Permitted search adapter | Attribution and extraction | Newly discovered verified company websites |
| E4 | News/social/job extraction changes | Independently verified sites | Family recall without attribution/date errors |
| E5 | Synthesis improvements | Same published claims | Better judged usefulness, no unsupported statements |
| E6 | Frontend improvements | Same profile data | Successful find/compare/verify tasks |
| E7 | Integrated candidate release | Frozen validation inputs and limits | Combined operational and accuracy gates |

Use paired snapshot replay for causal comparison and a separately declared live run for source availability. Do not silently warm caches for one arm. Include negative and failed experiments. A single unusually rich company must not dominate improvement claims.

Mandatory promotion gates:

- No observed material wrong-company publication or fabricated financial value in reviewed release outputs.
- All claims resolve to retained, permitted evidence; source audit passes.
- Every supplied input produces one valid terminal envelope within limits.
- Existing regression tests and newly justified behavior tests pass.
- No unsupported claim of population precision, recall or official score.
- Measured targeted benefit survives validation without a material regression elsewhere.
- Any unresolved material attribution dispute blocks that publication or the release until resolved.

Zero observed errors is a sample result, not proof of zero population error. Expand review when the sample is too small to support a conclusion.

## 12. Execution schedule and scope control

This is a proposed schedule, not completed work or a guarantee of turnaround.

| Window | Focus | Required output |
|---|---|---|
| First working day | Independent pilot labels; stage counters; baseline freeze | Reviewed failure inventory and reproducible baseline |
| Second working day | Budget allocation and targeted ownership traversal | Paired development results; reviewed new acceptances |
| Third working day | Best discovery/extraction changes; synthesis and UX gaps | Validation results and complete user-task checks |
| Final pre-cutoff window | Clean install, fresh scale run, audits, committed-code verification | Reviewable release package and exact revision identity |

If the cutoff leaves insufficient time, prioritize: contract/safety fixes → measured scale coverage → supported synthesis/verification UX → optional source expansion. Defer new paid providers, an LLM rewrite and a fully labeled 1,500-case corpus if they jeopardize release validation. Never claim deferred work is complete.

Keep production changes reversible and separately reviewable. The user will commit and push. Do not submit a hash from an earlier tree or imply that uncommitted changes are deployed. Email/submission requires the user's explicit instruction.

## 13. Verification commands and reproducibility

Existing commands below are examples using the pinned local environment. Use new output directories and the actual frozen input files. Confirm CLI help before adding new options. The local pilot is development data; it is not the release holdout.

```powershell
uv sync --frozen --group dev

.venv-audit\Scripts\python.exe -m pytest tests eval/diagnostics -q -p no:cacheprovider --basetemp=.test-tmp/rank-target-next --tb=short

.venv-audit\Scripts\signalpost.exe run --organisations out-website-pilot/companies.jsonl --out out-rank-target-smoke-next --workers 8 --job-days 7 --max-requests 2000 --max-minutes 45 --max-cost 10 --no-showcase

.venv-audit\Scripts\python.exe eval/snapshot_audit.py out-rank-target-smoke-next --output out-rank-target-smoke-next/source-audit.json

git -c core.whitespace=cr-at-eol diff --check
```

`uv sync` normally creates `.venv`; `.venv-audit` above refers to the already installed local audit environment. On a clean machine use the documented `uv run` entry point after frozen installation instead of assuming that audit environment exists. Workspace-local cache settings may be needed in this Windows sandbox; they are not evaluator requirements.

For each run record input hash, source snapshot/cutoff, code digest or exact commit, dependency lock hash, source access configuration without secrets, request/time/cost budgets, cache state, start/end time and label version. Publish aggregate reports; keep credentials, raw outputs and restricted source material ignored.

## 14. Release deliverables and definition of done

- [ ] Reviewed pilot labels and per-stage failure analysis, with unresolved cases explicit.
- [ ] Frozen independent validation/release inputs without known company/domain-family leakage.
- [ ] Same-budget comparison showing the promoted discovery/allocation changes help.
- [ ] Per-family precision/recall estimates where reference labels support them; sample sizes and intervals included.
- [ ] Fresh 100-company smoke and 1,100-company stress reports from the candidate code, with complete output and no hidden budget bypass.
- [ ] Evidence audit, meaningful Python regressions, frontend task checks and refresh replay pass.
- [ ] Source permissions, secrets, optional adapters and expected API costs documented in `SOURCES.md`, `.env.example`, README and submission materials.
- [ ] Clean checkout installs from the lockfile and runs using the declared command.
- [ ] Public sample is usable and evidence links work; sample generation is not misrepresented as official scoring.
- [ ] User commits/pushes; obtain the exact hash and verify it matches the tested code. If code changes after validation, rerun affected checks and update provenance.
- [ ] Submission package contains repo link, exact hash, evaluator command, model/API declarations, cost expectations and smoke report; revision slot and deadline checked.
- [ ] No guessed score, fabricated metric, unsupported ownership decision or unexecuted test described as measured.

The programme succeeds when a frozen revision improves independently checked coverage within budget while preserving exact attribution, useful explanations and verifiable UX. Only the organizer's shared evaluation can establish whether it beats the leader.

## 15. Supporting project documents

- [Latest pilot diagnosis](reports/website-pilot-20261112.md)
- [Latest release measurements and limitations](reports/release-readiness-20261112.md)
- [Detailed website benchmark design](docs/dev/deep-website-search-plan.md)
- [Existing improvement programme and risk history](docs/dev/metrics-improvement-plan.md)
- [Earlier rank-up plan](docs/dev/rank-up-plan.md), historical context; this document sets the new 82-point planning target.

This document coordinates the next programme. Existing reports remain immutable observations of their respective runs; newer targets do not retroactively change their metrics.

## Implementation checkpoint — 13 November 2026

Implemented the first scheduling/diagnostics increment and frontend reporting, with a fail-closed correction for interrupted identity traversal. The breadth strategy is explicitly selectable; `auto` preserves the existing scheduler until independent validation supports promotion. See [implementation results](reports/scheduling-improvement-20261113.md). This does not complete Phases A–H: independent reference labeling, broader source discovery, extraction/synthesis evaluation, transport pinning and final release holdout remain open. The 82-point target remains a target, not a measured result.
