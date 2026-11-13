# Website discovery pilot — 12 November 2026

## Delivered

Built a frozen 100-company development pilot from the official universe, verifying decompressed SHA-256 `b82d6a3e7231d1759a958c282bc4366b80ec2fab8095053d8ed7fa9cd01bc838`. Excluded 3,722 previously tested entities. The pilot contains 20 random companies, 40 potential positives, and 40 challenge cases (20 shared-host, 10 holding/investment/property names, 10 scoped paths). There are 82 universe website candidates. These strata are sampling hints, not ownership labels. Exact host matching does not establish domain-family isolation.

Local working artifacts (ignored by Git):

- `out-website-pilot/website-list.md`: all 100 entities with clickable candidates and observed gate decisions.
- `out-website-pilot/candidates.jsonl` and `manifest.json`: frozen selection and provenance.
- `out-website-pilot/probe/review-tasks.jsonl`: 100 blank independent-review tasks and search-query suggestions.
- `out-website-pilot/probe/observations.jsonl`: current registry anchor metadata, visited-page hashes and gate observations.
- `out-website-pilot-baseline/`: production outputs, snapshots and run report.
- `out-website-pilot/stage-diagnosis.json`: company-level comparison.

The frozen org-only input hash is `898034a4c5a825bc18f33d49f281903b43e4da6e41b7618d947282abcff89c51`. Production code SHA-256 is `6b71faa6dde5e8da89b2b43ecc6b5851db5a0a84a9efc143b3298752816345cb`; the run identifies agent revision `617212227de8`. New evaluation scripts remain working-tree changes.

## Measured runs

| Measure | Injected-candidate probe | Normal org-only baseline |
|---|---:|---:|
| Companies | 100 | 100 |
| Requests | 346 | 1,137 |
| Elapsed seconds | 95.1 | 239.6 |
| Declared external API cost | $0 | $0 |
| Companies with accepted/published website | 20 | 23 |

The probe generated 83 observations: 20 accepted, 28 ambiguous, 17 rejected, 11 unreachable, 6 blocked and 1 skipped platform. Seventeen companies had no probe candidate. The baseline published websites for all 20 probe-accepted companies and three additional companies. Thus this experiment reveals no probe-accepted/baseline-missed case; it does not establish that all accepted websites are correct.

Baseline website states: 23 available, 48 ambiguous, 19 not available and 10 blocked. It published social profiles for 9 companies, contacts for 55, descriptions for 13 and locations for 89. Registry identity, status, industry, financials, leadership and activity were available for all 100. Activity availability must not be interpreted as company-news recall. Jobs were blocked for all 100 because `NAV_FEED_TOKEN` was absent; no valid job coverage estimate follows from this run.

The stage comparison leaves 61 companies with unresolved/rejected/unreachable/blocked candidates and 16 without a probe candidate or baseline website. All 40 targeted challenge cases lacked published websites. This may reflect correct abstention, false rejection or inaccessible evidence; independent review must distinguish these.

Validation: 100/100 envelopes valid; 8,790 evidence entries audited, zero missing references or invalid objects/locators; 4,775 account claims and 1,183 filing-history claims verified against retained source records. This verifies source integrity, not full independent ownership precision. Python verification: 204 tests under `tests/` plus 71 diagnostic tests, all passing (275 unique tests). The eight new evaluation tests also passed in the diagnostic invocation.

## Findings and next work

1. Review all 23 published websites for legal ownership and relationship scope, and all nine social-profile companies for handle attribution. Review source pages independently of classifier explanations.
2. Review the 61 unresolved cases, prioritizing all 40 ownership challenges. Label correct abstention separately from false rejection, robots denial and network failure. Do not loosen the gate merely to improve publication rate.
3. Deep-search the 16 remaining no-candidate cases using exact org number, exact legal name, municipality, contact and permitted search APIs. Freeze any new discoveries separately before a paired rerun. A manual search for `922423466` surfaced a [Nor-Graphic PDF candidate](https://www.nor-graphic.no/assets/ng95.pdf); this remains a search candidate, not accepted claim evidence. The separate supplemental ledger does not change the frozen baseline. Manual research is outside the agent's reported request/cost budget.
4. Establish independently known-positive sites, then collect dated news details, exact-employer job ads and negative controls. Implement extraction-only evaluation once reference facts exist. The current scripts implement corpus construction, attribution probing and stage comparison only.
5. Supply an authorized NAV feed token for a separate declared job-source run. Preserve blocked states until access is available.
6. Expand toward the planned 1,500 entities only after the pilot labels and rubric are checked; isolate domain families across development and withheld evaluation splits. Repeat baseline and change runs with equal budgets and report random/challenge strata separately.

**Precision, recall, F1 and competition score remain unmeasured.** Website availability of 23% is not recall. This is a candidate-enriched development pilot, not a representative population estimate or a blinded score. No refresh interval has been evaluated in this experiment.

## Reproduce

Use fresh output directories; corpus and probe tools refuse existing output directories to preserve review work. Baseline receives only org numbers, never injected website candidates.

```powershell
.venv-audit\Scripts\python.exe eval/website_modes.py out-website-pilot --out out-website-pilot/probe-next --max-requests 1000 --max-seconds 600
.venv-audit\Scripts\signalpost.exe run --organisations out-website-pilot/companies.jsonl --out out-website-pilot-baseline-next --workers 8 --job-days 7 --max-requests 2000 --max-minutes 10 --max-cost 10 --no-showcase
.venv-audit\Scripts\python.exe eval/website_metrics.py out-website-pilot/probe-next out-website-pilot-baseline-next --output out-website-pilot/stage-diagnosis-next.json
.venv-audit\Scripts\python.exe eval/snapshot_audit.py out-website-pilot-baseline-next --output out-website-pilot/snapshot-audit-next.json
.venv-audit\Scripts\python.exe -m pytest tests eval/diagnostics -q -p no:cacheprovider --basetemp=.test-tmp/website-next --tb=short
```

Aggregate machine-readable results: [website-pilot-20261112.json](website-pilot-20261112.json). Full sampling and access plan: [deep-website-search-plan.md](../docs/dev/deep-website-search-plan.md).
