# Signalpost working reference

Updated 19 November 2026 from the supplied `scoring.pdf` (Builderr page captured 19 November, 21:41), the participant brief, evaluation contract v2, agent playbook, learning harness, source policy supplied in chat, and direct organizer feedback. Read this before working on the collector, evaluation, public UI, or submission.

See [how Builderr tests submissions](BUILDERR-EVALUATION.md) for the evaluator procedure and local equivalents, and [Signalpost source policy](SIGNALPOST-SOURCE-POLICY.md) for the source and publication guidance supplied in chat.

## Which rules apply

- Use the 19 November scoring PDF for the general score, qualification, submission, and revision rules below. Use the detailed evaluation contract for compatible technical requirements and Builderr's run-specific instructions for the actual batch, cutoff, output format, limits, network policy, and credentials.
- The PDF lists **November 22, 2026** for general entries and revisions, with four revisions after the first version (five exact commits total). Each revision freezes before its next official run and applies to later batches only. The earlier email's **November 15, 09:00 IST** applied to that specific rerun. Confirm the applicable deadline and frozen commit with Builderr when preparing another submission.
- The current submission artifact is a **100-company smoke-test result or report**. The initial 1,000-profile instruction is historical. Larger runs and public profile samples are useful for development and UX. Builderr evaluates the executable agent on the supplied batch.
- The playbook and learning harness guide implementation and experiments. They do not mandate a stack, LLM, or specific crawler.

## Scoring and qualification

| Dimension | Points | What to optimize |
|---|---:|---|
| Recall and coverage | 50 | For each external family, **70% company recall + 30% individual-claim recall** against the same independently checked pool. |
| Precision and evidence | 30 | Exact legal entity, correct fact, valid source, supporting span, and date. |
| Synthesis | 12 | Explain what the company does, what changed, and what remains unknown, with support for each conclusion. |
| UX | 8 | Find a company, compare two companies, and verify facts on desktop and phone. |

- An official run must reach **65/100 overall and at least 95% precision**. A checked claim must be both correct and attributed to the right company. Coverage and recall contribute to the score without independent qualification thresholds. A material wrong-company publication or fabricated financial value prevents an official result even if the visible score is high.
- Builderr verifies and deduplicates the pooled discoveries from all entrants and its crawlers, versions the pool, and rescores everyone against the same version. The earlier detailed contract reports recall as unmeasured when the pool lacks at least 15 positive company–field opportunities across at least three external families. Keep the directional 500-company leaderboard and its recall scaling separate from final ranking.
- Qualified rankings average scheduled daily batches while a frozen version is active. A builder-caused failure or missed batch scores zero after clean reproduction. Builderr harness, infrastructure, and shared-source failures are void and rerun with the same code. Tiebreak order is fewer wrong-company publications, higher weighted company recall, then lower declared third-party cost.

## Official execution and output

- Read the batch at run time, including unseen organisation numbers. Anchor legal identity to Builderr's frozen registry snapshot when supplied. The 411,160-company public universe is a development input. Declare external caches and enforce the supplied observation/evidence cutoff.
- Return exactly one terminal envelope per supplied company, including empty, blocked, ambiguous, or failed lookups. Use `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous`, and `failed` distinctly. Preserve reasons for missed or budget-limited discovery. Missing financial values stay missing.
- Cover legal identity and verified brand, filed accounts and history, leadership and workplaces, official websites and profiles, individual hiring ads and dated public activity, claim evidence and availability, plus refresh metadata, material changes, and errors.
- Fit the evaluator's time, outbound, and cost limits. Earlier instructions gave 45 minutes, 2,000 requests, and $10 in external API costs. Treat those as historical defaults and use the actual supplied caps for each official run. Count robots fetches, redirects, and retries in the request budget and preserve time to finish the output.
- Reproduce from a clean checkout at the exact commit with pinned dependencies, the declared install step, and one evaluator run command. Supply repository, branch when requested, exact hash, smoke report, models/APIs/licences, expected third-party cost, and contact details. Document safe outbound URL handling and server-side secret variables. Use evaluator-reproducible credentials where required.
- Include the agent name in the submission to `submit@builderr.ai`, as specified by the participant brief. LLM use is optional within the supplied API budget. The PDF says to request an evaluator model key if needed.

## Sources and claim publication

- Prefer official Norwegian registry and filing sources for legal identity, roles, workplaces, industry, employees, and financial values. A registry website or email domain is a candidate. Verify the exact organisation number in ownership context or unambiguous full legal identity on the relevant page before using it.
- Use verified company-owned pages, feeds, sitemaps, and structured data. Label parent, group, subsidiary, franchise, manager, and brand relationships separately. Attribute every published fact to its own entity and scope. A verified local legal/contact page can support its own claims. Shared-domain navigation or an unrelated customer, supplier, or agency mention cannot establish ownership.
- Check social handles and entity-controlled links individually. Reject shared group, theme, agency, and global-parent accounts unless exact company ownership is supported. Linking an account does not authorize fetching it.
- News requires a real detail post with substantive content, exact publisher scope, and an actual publication date. Reject menu text, utility pages, product listings, and dates derived solely from modified, updated, or sitemap metadata.
- Jobs require a single active ad tied to the exact employer or verified subunit, with source-supported dates and status where relevant. Reject search links, generic careers pages, expired ads, and parent vacancies. A verified company careers page can lead to a documented public job-board API. Follow [SOURCES.md](SOURCES.md) for current adapters and NAV access requirements.
- For every published claim preserve a durable source URL or identifier, retrieval time, effective/publication date or reporting period where relevant, content hash, supporting span or locator, extraction method, and entity/account scope. Keep these dates distinct. A company description is the company's own account and cannot substantiate independent sentiment. Financial values require the right filing, accounting field, currency/unit, period, and company/group scope.
- Use documented public or licensed APIs, licensed feeds, and pages whose terms permit the access pattern. Honor robots rules and safe URL controls. Search results and Wikidata supply candidates only. Unofficial connectors for LinkedIn, Meta, Glassdoor, Indeed, Google, or similar platforms require a permitted method. Private discovery experiments do not authorize competition use. Declare any connector used for scoring, show permission, and support published claims independently with a durable permitted source.

## Refresh, evaluation, and promotion

- Refresh on a frozen strategy. Preserve prior observations and evidence, emit typed material changes, and produce no duplicates or false changes when replaying the same snapshot. A temporary failure preserves prior support as explicitly stale history. A demonstrated ownership conflict revokes affected company-owned claims. Closed ads leave the current view. Keep stale history out of current coverage and public fact displays.
- Develop on public cohorts and keep an independently labelled, frozen opportunity set for validation. Record strategy version, candidate/rejection reasons, identity evidence, URLs/redirects, snapshot hashes, availability, errors, requests, runtime, and cost. Prefer bounded deterministic extraction with a documented fallback.
- The playbook recommends separate development, validation, and final cohorts without organisation or host overlap. It also recommends static and structured extraction first, browser rendering for confirmed JavaScript shells, and model use for candidate generation or supported synthesis. Keep exact-identity decisions grounded in evidence.
- Compare in order: wrong-company errors, supported-claim precision, evidence validity, useful coverage/recall, refresh correctness, then runtime and cost. Promote only with zero new material ownership errors, no meaningful precision loss, complete evidence for material claims, a declared useful coverage gain, and budget compliance. Record the decision and preserve rollback. Freeze code, dependencies, strategies, models/prompts, gates, sources, and budgets before official evaluation.
- Report exact-company precision, factual correctness, wrong-company count, per-family company and fact recall, evidence-span validity, completion and abstention, false changes, p50/p95 runtime, requests, and cost per company. Publish denominators, unresolved labels, and uncertainty. Envelope validity and availability describe execution. Recall needs a verified opportunity set. Report local evidence integrity and test results separately from independent claim correctness and Builderr scores.
- Retain attribution regressions for VESTSIDEN HAGEBY IV BORETTSLAG versus its manager and OTIS AS versus the global parent account and India site. The organizer disclosed two of eight wrong-company findings from the old scored commit. Keep those findings and later development runs attached to their own versions. See [organizer diagnosis](reports/organizer-diagnosis-20261114.md) and [recovery validation](reports/recovery-validation-20261114.md).

## Public experience and JBOX

- Show exact legal identity, reporting periods, source scope, freshness, and unknowns. Make find, compare, and claim evidence work on desktop and phone. Present a dated sample as such, with its included families and limitations.
- The PDF gives the separate JBOX bonus site deadline as **November 7, 23:59 IST**. Its voting banner says November 16. The general November 22 revision extension does not establish a JBOX extension. Verify live flows, data provenance, and bonus eligibility before claiming them. Gallery admission requires qualification, and public voting does not affect technical rank. See the [JBOX checkpoint](docs/dev/jbox-build-checkpoint.md).
- The PDF lists main prizes of $1,200, $500, and $300, plus separate JBOX prizes of $250, $150, and $100 for sites built with JBOX. It also lists four $100 community-vote awards on September 6, September 20, October 4, and October 18. The general result and winner announcement dates were pending evaluation in the capture.

## Source record

- `scoring.pdf`, supplied 19 November 2026. Pages 3–4 cover submission and execution, 5–7 scoring, qualification and ranking, and 8 revision rules and JBOX. SHA-256 `6dede47c859cb9bf1c0868b3d47566e9abae02f54339ea133b5ccccf60952231`. [Builderr scoring page](https://builderr.ai/challenges/signalpost#scoring)
- Participant brief, evaluation contract v2 (effective 26 August 2026), agent playbook, and learning harness supplied as chat attachments. The dated PDF supersedes the older qualification summary and general revision deadline.
- Signalpost source policy supplied in chat and direct organizer feedback on the original submission. Current repository source declarations are in [SOURCES.md](SOURCES.md).
