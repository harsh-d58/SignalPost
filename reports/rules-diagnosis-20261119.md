# Signalpost rules audit and test diagnosis, 19 November 2026

**Upgrade follow-up.** The findings below describe the baseline commit. After the diagnosis, the four failing probes became ordinary passing regressions. The upgraded build requires a whole normalized identity value for the name-only check and counts each article paragraph once. [Cohort validation](cohort-validation-20261119.md)

**Verdict:** the agent meets the batch-completion and retained-evidence checks on the measured cohorts. Exact-company attribution fails three new offline publication cases. This is a release risk under Builderr's material wrong-company rule. No independent evaluation establishes 95% checked precision, pooled recall, or a 65-point score for this revision.

Scope: local checkout `6a87ab71d7c0c24af0017851630d6f6ac4631f52`, the [working rules](../SIGNALPOST-RULES.md), [evaluation procedure](../BUILDERR-EVALUATION.md), [source policy](../SIGNALPOST-SOURCE-POLICY.md), code, regressions, and saved November 14 outputs. The saved batch source digest starts `04906cd1`; today's byte-level digest starts `2bb4d854`. The digest includes source files, lockfile, and source declarations. The historical runs show behavior of that recorded build. No fresh live batch or private Builderr evaluation was performed in this audit.

## Core rules before score optimization

| Rule | Finding | Evidence and limit |
|---|---|---|
| Consume supplied batch under budget | Demonstrated on saved runs | 100/100 in 225.5 s and 666 requests. 1,100/1,100 in 288 s and 1,920 requests. Both reported $0 external API spend. The larger run returned envelopes even for three unresolved identities. |
| Frozen inputs, explicit states, and cutoff | Regression coverage | Batch and evidence-contract tests cover supplied snapshots, missing identity, malformed input, timestamps and periods. The historical live runs used live registry data. |
| Exact-company ownership | **Fails targeted cases** | An embedded legal name in the title plus a shared email domain can license publication of the whole website. See reproductions below. |
| Evidence and financial values | Passed offline artifact audit | 70,983 evidence entries, 70,695 source locators, 288 excerpt checks, 48,707 verified account claims, zero invalid account claims or missing references on the saved 1,100. Independent semantic support for web claims still needs review. No filing-history claims were verified in that audit. |
| News and active jobs | Mixed | Known utility-page negatives pass. A layout-dependent article-body check fails. The scale run emitted two news claims and zero jobs. Both Northstore titles have published-date evidence, but the retained title/date do not settle whether the pages contain substantive news. |
| Source rights, credentials and reproducibility | Partly demonstrated | Declarations cover declared source classes and blocking NAV without deployment credentials. CI defines clean setup, Python and frontend checks. This audit ran in an existing environment. A clean evaluator install, platform permissions in the deployment, and full outbound safety require separate evidence. |
| Idempotent refresh, preserving and revoking evidence | Regression coverage | Tests cover same-snapshot replay, temporary source failure, closure and ownership revocation. The OTIS replay previously revoked two old claims. A bad website accepted again never triggers an ownership-loss decision. |
| Synthesis, UX and official scoring | Partly demonstrated | 18 local frontend regressions passed. Grading synthesis quality, JBOX phone/desktop behavior, and comparison with Builderr's pool needs independent review. Historical 14/22 correctness belongs to `eaef804`. |

## Reproducible failures

Run `uv run --group dev pytest eval/diagnostics/test_identity_and_article_boundaries.py -q` to exercise these cases. At baseline the four assertions below failed. The synthetic fixture uses an offline fetcher.

| Case | Expected | Observed | Cause |
|---|---|---|---|
| Target OTIS AS, title “West OTIS AS” | Withhold the other company's site | Official website published | Contiguous-token matching accepts the target as a suffix of a different legal name. |
| Title “Customer story: OTIS AS” | Withhold the customer's host | Official website published | A page subject in title metadata qualifies as owner identity. |
| Title “OTIS AS &#124; Otis India” | Withhold conflicting regional scope | Official website published | A shared org email domain and a title containing the legal name outweigh the unresolved region in this case. |
| A single short catalogue invitation inside nested main/article | Insufficient article prose | Article classifier accepts | The classifier reads the same paragraph from both ancestor roots. This probe reaches classification only. Final publication also requires an eligible URL, ownership and date. |

Positive control “OTIS AS” published and negative control “Otis Worldwide” abstained with the same registry candidate and email. Existing CI Python suite passed 318 cases. Separately, six new probes produced two passes and four expected failures. The three website failures reach the publication entry point. A verified-site decision can also affect contacts, descriptions and linked activity.

## Why coverage is low

The machine report for `run-20261114T170034Z` shows 73 companies attempted for websites, 68 completed checks and 1,024 companies unattempted for budget. Failed bulk roles/workplaces downloads left 1,016 failed family states in each family. Only 20 companies had a website available, seven had social accounts and seven had a description. Activity was available for 1,096 companies, largely from 4,257 registry events. Two company-news claims belonged to NORTH INDUSTRI AS. All 1,097 resolved entities had a blocked jobs state. This demonstrates poor external discovery coverage and incomplete opportunities to search. It does not quantify how many eligible sites or jobs were missed.

## Fix order and acceptance cases

1. Separate publisher identity from page subject and require stronger ownership context on shared domains. Preserve exact standalone legal-name and org-number controls, legal/contact-page scope, and the existing regional and manager negatives. Repeat the three failing publication probes and review abstentions on genuine multi-part titles.
2. Count each paragraph once and exclude unrelated markup from eligible prose. Compare identical short and substantive stories under flat and nested markup. Recheck the Northstore candidates for article body, publisher, published date and product-page evidence.
3. Compare fallback and website scheduling on identical saved responses. Measure companies reached per request, failed official-record coverage, and independently supported external additions. Use verified open individual ads and rejected parent/landing pages as live jobs controls.
4. Before quoting qualification metrics, freeze a labelled holdout with no organisation or host overlap, independently review ownership and claim support, and publish per-family denominators, abstentions, unresolved cases and uncertainty. Repeat the smoke run from the frozen revision with the supplied settings.
