# Rank-up revision — 10 November 2026

The bulk route materially improves registry coverage within the same request cap. The current revision also adds frozen identity anchoring, retained evidence, cutoff handling, stronger publication gates and reproducible evaluation tools. **The competition score remains unmeasured.**

## Measured results

| Metric | Smoke: 100 companies | Direct: 1,100 companies | Bulk: same 1,100 companies |
|---|---:|---:|---:|
| Terminal envelopes | 100/100 | 1,100/1,100 | 1,100/1,100 |
| Requests | 647 | 1,920 | 1,920 |
| Live elapsed time | 215.8 s | 120.2 s | 407.4 s |
| External API cost | $0 | $0 | $0 |
| Legal identity | 100 | 1,098 | 1,098 |
| Financials | 100 | 1,091 | 1,091 |
| Leadership | 100 | 133 | 1,098 |
| Workplaces | 79 | 105 | 839 |
| Websites | 4 | 18 | 28 |
| Social profiles: companies covered | 1 | 7 | 10 |
| Company news: companies / posts | 1 / 3 | 4 / 12 | 5 / 12 |
| Jobs | 0 | 0 | 0 |

Counts represent companies with current claims unless stated otherwise. Two scale inputs were unavailable in the current entity API and still received terminal envelopes. Registry events are reported separately from company news. The bulk run published 76,225 current claims. Its per-company worker p50/p95 were 312/3,609 ms; these exclude shared bulk-download time, which is included in the 407.4-second total. Smoke p50/p95 were 8,250/15,906 ms, including the paced filing-history lane.

Evidence: [smoke metrics](rankup-smoke100-metrics.json), [bulk metrics and comparison](rankup-scale1100-metrics.json), [direct metrics](rankup-scale1100-direct-metrics.json).

## Verification

- Pinned dependencies installed successfully into a fresh Python 3.12 environment. [Final test output](rankup-tests.txt).
- Scale artifact audit: **75,475/75,475 checks passed**, consisting of 75,154 retained source locators and 321 excerpt artifacts. No missing references, invalid objects or invalid locators. [Report](rankup-scale1100-verified-snapshot-audit.json).
- Smoke artifact audit: **7,836/7,836 passed**, including 38 excerpt artifacts. [Report](rankup-smoke100-verified-snapshot-audit.json).
- Fresh source check: **100/100 excerpts re-found**, zero fetch errors. This measures source support availability, not population precision. [Result](rankup-live-evidence-check.txt).
- Direct/bulk parity: **60/60 checks across 30 companies passed**, covering roles and workplaces, including absent workplaces. [Report](rankup-bulk-parity-verified.json).
- All **28 published scale websites** passed a fresh exact-entity gate check. This is deterministic revalidation, not an independent precision estimate. [Attribution report](rankup-website-attribution.json).
- Repeating the registry parser on retained sources produced identical envelopes. Refresh over all 1,100 profiles produced **zero false changes**. [Batch replay](rankup-batch-replay.json). Controlled new filing, leadership, workplace, address and job changes also passed. [Refresh replay](rankup-refresh-replay.json).
- Showcase search, comparison, source drawers, keyboard navigation and language/theme interactions passed with no JavaScript errors. Code-only recheck on 11 November passed against both the recent 100-company output and the legacy 1,000-company Pages dataset. This is a jsdom interaction check, not a fresh visual/mobile audit. [Interaction check](../eval/ui_check.cjs).
- A deliberately exhausted run emitted all 100 envelopes, used zero requests and exited with failure. Its report correctly rejects execution success. [Constrained report](rankup-constrained-run-report.json).

The 11 November code review fixed malformed-route decoding, invalid persisted comparison state, fractional/out-of-range pagination and unresolved concurrent profile loads after a failed or incomplete script download. All 14 new [frontend regression cases](../eval/ui_resilience_check.cjs) pass. The Python suite was rerun with **164 passing tests**, and the retained scale evidence audit again passed **75,475/75,475 checks**. These checks used existing artifacts and fixtures, without a new live collection or an official scoring run.

## Corrections and provenance

The initial bulk experiments hit role-download/parsing deadlines. The revised parser avoids repeated large string copies, checks deadlines between network chunks and uses bounded download/parse windows with direct fallback. The successful scale run downloaded roles in 277 seconds and workplaces in 131 seconds.

Full artifact checking then caught incorrect municipality JSON pointers. Direct/bulk comparison found four address-separator mismatches. Both were fixed. The scale artifacts were reparsed from their retained sources, normalizing 134 address renderings without changing substantive company facts. The original live artifacts remain in `out-rankup-scale1100`; corrected artifacts are in `out-rankup-scale1100-replay`. Their report explicitly preserves the live collection measurements and separately identifies the offline replay, original envelope digest and parser version. **The replay is not presented as another live run.** The fresh smoke run includes the municipality fix; the final address normalization and identity-quote refinements have focused regression tests and fresh source checks.

Source locators, original-response hashes and retained-object hashes are distinct. Registry JSON is privacy-minimized. Company pages and NAV retain excerpts instead of raw pages. An excerpt-integrity check cannot independently prove a full page's content or exact attribution. No measured overall precision or official recall is claimed.

Frozen identity is authoritative when `--registry-snapshot` and its observation timestamp are supplied. Missing frozen records do not fall back to a different live identity. `--evidence-cutoff` excludes later observations. NAV requires an approved credential; the experimental public token is now an explicit private-development option. News and jobs require their individual detail pages. Website name proof must occur within a single identity field, and the retained quote contains that proof.

## Promotion decision

Use **`--bulk-files --workers 8 --job-days 7` for large batches**, retaining direct mode for small runs and fallback. Against the same 1,100 companies, leadership improved **87.73 percentage points**, workplaces **66.73 points**, websites **0.91 points** and social coverage **0.27 points**, with unchanged requests and financial coverage. The declared 10-point role/workplace floors and parity checks pass. The cost is 287.2 additional seconds and large bulk transfers. Earlier failures remain recorded rather than discarded.

The revised one-command evaluator invocation is in [README](../README.md). Keep the organizer's supplied snapshot, timestamps, limits and credentials explicit. The output directory contains private evidence and should not be published wholesale. The working tree has not been committed or submitted; an exact release commit remains required.

## Score scenarios, not predictions

Current scoring is 50 coverage, 30 evidence, 12 synthesis and 8 UX. [Official scoring](https://builderr.ai/challenges/signalpost#scoring).

| Conditional scenario | Coverage | Evidence | Synthesis | UX | Total |
|---|---:|---:|---:|---:|---:|
| Qualification sensitivity | 24 | 28 | 8 | 5 | 65 |
| Above the previously posted 70.43 leader | 28 | 29 | 9 | 5 | 71 |
| Planning target | 32 | 29 | 10 | 6 | 77 |

These component values are assumptions, not locally measured judging scores. Website coverage of 2.55%, social coverage of 0.91%, news across five companies and zero verified jobs remain the main competitive risks. Full registry coverage alone does not establish sufficient pooled recall. No reliable total-score prediction is possible without Builderr's checked reference collection and reviewer scores.

Next experiments should concentrate on permitted company-owned job/ATS detail pages and verified website/news discovery. Licensed reviews/sentiment, browser rendering and filing-PDF extraction remain separate unimplemented experiments. The frozen cohorts are engineering samples with exact-known-host partitioning; parent-group isolation and independent recall labels remain incomplete. No paid model is used, and the $0 figure excludes compute, bandwidth and development tools.
