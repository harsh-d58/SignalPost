# SignalPost batch accuracy diagnosis

11 November 2026. This evaluation covers publication rules, evidence integrity, claim-to-record accuracy, refresh behavior and the live company batch. The [fix plan](batch-accuracy-fix-plan.md) translates the findings into implementation and verification steps.

## Test inventory

| Suite | Cases | Passed | Failed |
|---|---:|---:|---:|
| Main regression suite | 175 | 175 | 0 |
| Existing improvement diagnostics | 14 | 9 | 5 |
| Additional batch accuracy probes | 19 | 11 | 8 |
| Total | 208 | 195 | 13 |

The diagnostics are opt-in acceptance cases. The five previously open cases reproduced the same failures. The newer probes use a fixed clock and mocked responses. Reproduce them from the repository root:

```powershell
uv run --frozen --group dev pytest tests eval/diagnostics -q -p no:cacheprovider --tb=short
```

## Confirmed accuracy and evidence defects

| Severity | Observed failure | Root cause and effect |
|---|---|---|
| High | Equal amounts in company and group accounts resolve to the same evidence record in a synthetic fixture. The retained baseline shows 11 scope mismatches. | The evidence ID in `model.py` omits the locator. The first evidence entry for an ID wins, so distinct financial records can share the first record's pointer. The reported amount can agree while the evidence points to the wrong scope. |
| High | The snapshot audit passes when a published financial value, currency or period is altered with the source and locator intact. All three mutations reproduced this. | `eval/snapshot_audit.py` checks the evidence and the locator against the retained object. It does not compare the published claim fields to that record. Audit success can therefore coexist with a claim-to-record error. |
| High | A website vacancy and a company article each pass with a name-only `ASA` employer or publisher when the target fixture is `AS`. | The name-only fallback in `_employer_matches` removes legal-form tokens. An explicit conflicting organisation number is still rejected. This creates a potential exact-company attribution error when identifiers are absent. |
| High | A vacancy with recent structured metadata and explicit closure text on its detail page is still published. | When there is no deadline, recency alone can qualify the vacancy. The website extractor does not check the closure text. Offset timestamps correctly reject expired ads in the accompanying tests. |
| High | An article whose only time marker is `class="unpublished"` is published as dated news. | The HTML date check matches the substring `published` within `unpublished`. The modification-only, wrong-organisation-number and product-page controls were correctly rejected. |

The [additional diagnostic fixtures](../../eval/diagnostics/test_batch_accuracy.py) document all 19 scenarios. The wrong-employer, closed-vacancy and unpublished-article examples are controlled cases. Their frequency in live output has not been established.

## Remaining coverage and reporting problems

| Case | What failed | Practical impact |
|---|---|---|
| D01 | Contact-page identity with exact legal name and corroborating registry phone remains ambiguous. | Websites can be missed when the homepage uses a brand and the legal name is on a contact page. |
| D05 | A registry event hides unknown company news in the brief. | A reader can mistake available registry activity for complete news research. |
| D06 | Two identical cacheable requests both reach the transport. | Duplicate requests leave less capacity for checking additional companies. |
| D07 | The console omits bulk mode and worker settings. | Manual batches can use a different execution path than the intended CLI batch. |
| D08 | An article reachable only through the linked sitemap is missed. | Eligible posts can be outside the current page and feed discovery routes. |

The three publication fixes from the previous pass and semantic reference matching all pass their targeted diagnostics. The older regression controls still cover exact owner acceptance, wrong parent rejection, and NAV blocking without a credential.

## Retained baseline cross-check

The archived run `out-rankup-scale1100-replay2` has 1,100 company envelopes. The standard audit verified 75,154 source locators and 321 excerpt artifacts, with zero unresolved references, bad digests or invalid locators.

I then joined each current financial claim carrying a record pointer to its actual retained record and compared owner, scope, amount, currency and period. Of 48,756 current financial claims, 42,616 carried account-record pointers. **42,605 of those 42,616** bound to a matching record. The other **11** pointed to a different scope, with the checked owner, amount, currency and period agreeing. The 6,140 financial claims without an account-record pointer were outside this comparison. Replaying the same 1,100 envelopes at their recorded completion time produced zero business changes.

For example, the 2024 `long_term_debt` claims for organisation `985446474` carry different account scopes but share evidence ID `ev-92a47778f9c94a68`. Its pointer resolves to a `KONSERN` record for both claims. The controlled refresh replay on the retained batch also passed its three checks for unchanged data, typed changes and carry-forward after an unreadable source.

The record comparison measures linkage for the checked fields. The excerpt check establishes that retained fragments match their envelopes and hashes. Estimating factual precision and recall still requires independently adjudicated claims and positives, including websites or jobs the agent did not find.

## Live scale run

The current agent was launched on the existing 1,100-company engineering cohort with bulk roles and workplaces, 8 workers, a seven-day job window, a 2,000-request cap, a 15-minute limit and a $10 cost ceiling. The repeated cohort permits comparison with the retained baseline. Its prior use limits what this run can establish about unfamiliar companies.

```powershell
uv run --frozen signalpost run --organisations eval/rankup/scale-1100.jsonl --out out-programme-scale1100 --bulk-files --workers 8 --job-days 7 --max-requests 2000 --max-minutes 15 --max-cost 10 --no-showcase
```

Run `run-20261111T091855Z` exited successfully and passed the runner's envelope and execution checks. Its agent version is `de11bc45be98-dirty`, with code SHA-256 `badf1d5a3a6f6834a3a7fc276b162b477b65a6ecff89f372d01640d8cd0a9700`. The current and retained runs have the same ordered input digest.

| Measure | Retained comparison | Fresh live run |
|---|---:|---:|
| Company envelopes | 1,100 | 1,100 |
| Identity and leadership, companies per family | 1,098 | 1,098 |
| Financials | 1,091 | 1,091 |
| Workplaces | 839 | 839 |
| Group relationships | 78 | 8 |
| Verified websites | 28 | 22 |
| Company social profiles | 10 | 9 |
| Dated company news | 5 | 5 |
| Verified jobs | 0 | 0 |
| Requests | 1,920 | 1,742 |
| Elapsed seconds | 407.4 | 702.0 |
| Declared third-party cost | $0 | $0 |

All coverage counts use companies as the denominator. The live run emitted 82,669 claims. Seven companies failed to yield financial claims and two had no registry entity. Website states were 22 available, 34 ambiguous, seven blocked, seven unavailable and 1,030 failed due to website request allocation or exhaustion. Sixteen website claims cited organisation-number proof and six used other identity signals. NAV performed zero feed requests because the approved token was unavailable. The zero job result gives no live evidence about job eligibility or vacancy precision.

**Time and request interaction.** Role and workplace bulk work took 543 and 302 seconds respectively, with overlapping execution. The company phase finished at about 691 seconds. With a 72-second safety reserve, the retry pass had roughly 137 seconds available, below its 180-second minimum. It did not run. The earlier batch spent 178 requests in that pass and recovered 70 group states and 58 website states. The fresh run left the same number of requests unused below the 1,920 usable cap. This explains the missing retry opportunity and the group coverage drop. Source changes and fetch ordering can also change the individual website results, so the coverage difference does not isolate the effect of the recent code changes.

**Evidence and refresh.** The fresh run passed 75,016 source-locator checks and 321 excerpt-integrity checks. The separate claim-to-record check again found **11 scope mismatches among 42,616 financial claims with account-record pointers**. The other 42,605 matched the checked fields. The full 1,100-envelope replay produced zero business changes, and the controlled mutation replay passed all three checks.

```powershell
uv run --frozen python eval/snapshot_audit.py out-programme-scale1100
uv run --frozen python eval/refresh_replay.py out-programme-scale1100/envelopes.jsonl .test-tmp/programme-live-refresh.json
```

The live batch and fixtures establish completion, observed coverage and specific correctness defects. Exact-company precision, claim recall and the official score remain unmeasured because this cohort has no independently adjudicated reference set.
