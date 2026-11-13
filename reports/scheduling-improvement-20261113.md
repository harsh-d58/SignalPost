# Scheduling improvement checkpoint — 13 November 2026

## Decision

Keep the existing scheduler as the default. The new breadth-first strategy is available with `--website-strategy breadth` for controlled evaluation. `auto` resolves to `legacy` until independent ownership labels and validation support promotion. This prevents an experimental allocation policy from silently replacing the submitted behavior.

The default path does receive the safety correction and diagnostics: incomplete identity traversal cannot fall through to weaker name-based acceptance, and a later budget refusal preserves an earlier completed ownership decision.

## Implemented

- Candidate rounds: one full candidate check per company before alternatives. The per-site identity checks are preserved; this is not homepage-only verification.
- Explicit candidates precede speculative domain guesses. Guesses are resolved lazily inside budget-checked workers rather than eagerly for the whole batch.
- Pending candidates survive interrupted work; completed rejected candidates need not be repeated in the next round. Prior ambiguity is preserved across candidate rounds.
- Request/time interruption during contact-page traversal leaves the candidate incomplete and unpublished.
- Run-level and company-level diagnostics distinguish attempts, completed candidate checks, pending candidates, budget interruptions and companies never attempted because of budget. These are not accuracy labels.
- `website-diagnostics.json` stores the detailed local trace; `run-report.json` includes aggregate counters and the selected strategy.
- Console and showcase display execution counts and explicitly distinguish them from precision/recall. Reports created before these fields existed still render.
- Final follow-up fixes preserve completed states on a later budget refusal and include website-round time in per-company timing totals.

## Live measurements

| Cohort | Historical existing pipeline | Breadth experiment |
|---|---:|---:|
| Pilot valid envelopes | 100/100 | 100/100 |
| Pilot websites | 23 | 23 |
| Pilot social-profile companies | 9 | 9 |
| Pilot requests | 1,137 | 1,099 |
| Pilot seconds | 239.6 | 332.8 |
| Scale valid envelopes | 1,100/1,100 | 1,100/1,100 |
| Scale websites | 29 | 38 |
| Scale requests | 1,920 | 1,920 |
| Scale seconds | 429.3 | 567.9 |
| Declared API cost | $0 | $0 |

The scale comparison gained 12 websites and lost three, for a net nine additional publications. The improvement is 31% relative to the historical count, or 0.82 percentage points of all 1,100 inputs. Neither figure is a recall gain: independent reference opportunities remain unlabeled.

The scale experiment attempted 127 companies and completed at least one candidate check for 116. It recorded 12 budget interruptions and 970 companies with no attempted candidate because of budget. Some of those companies may have no valid website at all; their website absence was not established by this run. The old run lacks equivalent attempt telemetry, so a live attempted-coverage gain cannot be calculated retrospectively.

The three lost websites were:

- `924351225`: identity check interrupted by budget.
- `877218872`: website phase exhausted before verification.
- `957938248`: a blocked first candidate followed by budget exhaustion; the final reporting fix now preserves the completed blocked decision rather than overwriting it with a generic failure.

Retained proof spans for the 12 gains contain exact org-number evidence for seven and corroborated legal-name/contact evidence for five. Inspecting these extracted spans is not a complete independent ownership audit. No accuracy labels were created from classifier decisions.

Runtime increased. The scale run spent about 408 seconds loading the roles bulk source before company processing. Network conditions and changed source timing confound the comparison; the slower run cannot be attributed solely to scheduling. The source models and deadline behavior still need a matched replay benchmark before stronger causal claims.

## Verification

- Controlled equal-budget fixture: three companies receive completed candidate checks with breadth versus two with legacy at 12 requests. No rejected candidate is published.
- Regression cases cover deferred guesses, incomplete identity traversal, candidate retry, retained ambiguity, preserving completed states on later refusal, and default-strategy compatibility.
- Source audit passed for both live runs. Scale: 75,564 evidence entries audited and 48,707 account claims verified; no missing references or invalid objects/locators/account claims.
- Frontend resilience: 16/16 tests passed, including old and new run-report shapes.
- Headless console check: no reported errors or problems; temporary server stopped after verification.
- Refresh replay: identical-snapshot idempotence, typed changes and evidence-preserving carry-forward all passed. The first invocation supplied a directory instead of the required JSONL path; the corrected invocation passed.
- Final Python suite: 282/282 passed. Generated-showcase interaction check: no errors or problems across navigation, profiles, evidence drawers, comparison, language switching and keyboard interactions.

## Provenance and limits

The machine-readable [manifest](scheduling-improvement-20261113.json) records each run's code digest, input hash and UTC timestamps. User-facing report date is 13 November in Asia/Calcutta; the runs themselves began on 12 November UTC.

The 100-company experiment preceded the lazy-guess follow-up and frontend additions. The scale experiment includes those changes but precedes final state-preservation, timing and default-selection corrections. Those final changes are regression-tested; neither live run is represented as a final-code full-batch run. Both comparisons use historical live baselines rather than an immutable source replay. No paid APIs were used.

This is one implementation increment, not completion of the full improvement programme. The strategy is opt-in because a larger publication count alone cannot establish exact-company precision. No official score, precision, recall or F1 estimate follows from these results.

## Next work, in order

1. Independently adjudicate all newly published websites and the losses; preserve label versions and source scope.
2. Construct replayable candidate snapshots and compare both strategies under identical request accounting. Investigate the three displaced websites and how alternative-candidate ordering affects them.
3. Measure which company–family opportunities are lost to account/group reserves and which can be recovered without sacrificing required official data. The 970 unattempted cases show that candidate rounds alone do not solve scale coverage.
4. Evaluate source-specific discovery, verified news/social/job extraction and authorized NAV access against labeled reference facts.
5. Complete the planned synthesis and frontend user-task evaluation, connection-time DNS protection and fresh release holdout.
6. Promote a default strategy only after the plan's independent accuracy and operational gates pass; then run the exact committed code on fresh smoke and scale inputs.

## Reproduce safely

Use fresh output directories. The local pilot and scale cohort are development material, not a withheld release set.

```powershell
uv run --frozen signalpost run --organisations out-website-pilot/companies.jsonl --out out-breadth-pilot-next --website-strategy breadth --workers 8 --job-days 7 --max-requests 2000 --max-minutes 10 --max-cost 0 --no-showcase
uv run --frozen signalpost run --organisations eval/rankup/scale-1100.jsonl --out out-breadth-scale-next --website-strategy breadth --bulk-files --workers 8 --job-days 7 --max-requests 2000 --max-minutes 15 --max-cost 0 --no-showcase
uv run --frozen python eval/snapshot_audit.py out-breadth-scale-next --output out-breadth-scale-next/source-audit.json
uv run --frozen --group dev pytest tests eval/diagnostics -q -p no:cacheprovider --basetemp=.test-tmp/scheduling-next --tb=short
node --test eval/ui_resilience_check.cjs
```

To retain existing allocation explicitly, use `--website-strategy legacy`, or omit the option. No commit, push, email or deployment was performed.
