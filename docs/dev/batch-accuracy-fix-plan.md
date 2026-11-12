# SignalPost batch accuracy fix plan

11 November 2026. The [batch diagnosis](batch-accuracy-diagnosis.md) records the cases and measurements behind this order. Fix the financial evidence link and wrong-company publication cases before expanding discovery.

The implementation passed all 217 regression and diagnostic cases and the console smoke test. The stricter audit detects 11 mismatches on the original retained batch. Re-extracting account evidence verified all 42,616 claims with an account-record pointer and cleared all 11 mismatches. Another 6,140 financial claims lack an account-record pointer and remain outside claim-to-record verification. All 1,100 envelopes kept the same claim content and the refresh comparison emitted zero changes.

The live 100-company validation run exercised the main fixes before the final legal-form guard and console display adjustments. It returned 100 envelopes in 218 seconds using 593 requests at $0 external API cost. It found nine verified websites, two articles for one company and zero jobs. NAV access was unavailable. The offline replay did not measure live scale coverage or throughput. Overlapping accounts with bulk downloads and scoring against an independent reference pool remain separate validation work.

```powershell
uv run --frozen --group dev pytest tests eval/diagnostics -q -p no:cacheprovider
uv run --frozen python eval/replay_registry.py out-programme-scale1100 out-programme-scale1100-repaired --accounts-only
uv run --frozen python eval/snapshot_audit.py out-programme-scale1100-repaired
```

## 1. Bind each financial claim to its source record

In `model.py` and `registry.py`, distinguish evidence from separate account records even when the amounts, fields, periods and response hashes are identical. Include the source record and field locator in evidence identity when a locator exists. Preserve the IDs loaded from prior runs so archived references still resolve. Add account scope to the locator alongside organisation number, period and currency. Review the audit-status and accounting-rules paths for the same ambiguity.

In `eval/snapshot_audit.py`, walk published claims and check each financial claim against the referenced record. Compare the amount, field path, currency, period, account scope and exact organisation number. Return a count of claims that could not be verified because the record has no owner or no suitable locator. Apply the same checks to older output where the retained data supports them. Fail validation when a claim points to a conflicting record. An endpoint scoped to one organisation can be reported as a separate form of attribution when the response omits the owner.

Re-run the equal-amount company and group case and the altered amount, currency and period cases. Add wrong-owner and wrong-scope mutations. Re-extract the retained batch and audit all financial claims with account-record locators. Compare refreshed claims by their values and source records to confirm that changing the evidence ID alone creates no business change.

## 2. Tighten vacancy and article publication

- **Legal identity.** Keep exact organisation number as the strongest proof. For name-only website job and article publisher checks, preserve explicit legal-form and branch qualifiers. Require a corroborating identity link when an abbreviated name or shared brand would otherwise identify multiple entities. Test AS versus ASA, parent versus subsidiary, and an exact name paired with a foreign organisation number.
- **Vacancy status.** Make explicit closure on the detail page override recent structured metadata. Require a future deadline or another current application signal for a vacancy that has no explicit status. Keep exact UTC expiry comparisons and the existing NAV credential and active-status rules. Test closed, expired, live and indeterminate ads, including date-only deadlines and offset timestamps.
- **Article dates.** Recognize explicit publication markers and reject negative or modification labels. Validate the publisher on the individual article, especially under a group or shared domain. Extend the fixtures to include listing pages, archived notices, product pages and third-party articles hosted on the same domain.

For every positive case, check that retained evidence supports the exact entity, item URL and applicable date or status. Review the newly accepted and rejected cases before changing the publication rules further.

## 3. Fix the existing coverage and configuration gaps

| Open case | Change | Verification |
|---|---|---|
| Contact-page identity | Bind the contact page's name and phone evidence to the candidate entity and site scope. | A verified contact page can establish the correct entity. Parent sites, customer lists and conflicting IDs remain rejected. |
| Unknown company news | Report dated company articles separately from registry activity and show whether article discovery completed. | A registry-only profile still shows company news as unknown. |
| Duplicate fetches | Reuse eligible responses within the same run. Keep request context, cache directives, robots policy and credentials in the eligibility decision. | An identical cacheable request saves one outbound request. Failed, expired or differently authorized responses retain their own behavior. |
| Console options | Pass bulk mode and worker count through the console and display the effective values from the run report. | Console and CLI runs with the same inputs produce the same effective configuration. |
| Sitemap discovery | Add bounded discovery for site-owned sitemaps and fetch the individual candidate article. | Sitemap-only articles with a publication date are found. Modification dates, wrong publishers and product pages remain excluded. |

Instrument attempts by candidate source and disposition, including budget skips. Use the saved requests to give more companies one identity check before following extra pages on a company already visited. Compare verified company-family gains at the same request cap.

Track bulk transfer and parse time independently. The live role lookup took 543 seconds before the per-company phase. Test overlapping account work with the bulk download, keeping the existing per-source caps and bounded direct fallback. Compare elapsed time and coverage under a normal response, a delayed bulk response and a failed bulk response. Preserve the ability to write one terminal envelope per input when a source stalls.

Test recovering unused request allocations before the final retry pass. The live run left 178 usable requests while 71 group results failed and website checks exhausted their own allocation. Reserve a small amount of time for finalization and let eligible retry tasks run only when their measured cost fits the remaining time. Replay the observed 543-second bulk delay with a fixed clock and compare terminal completion, group coverage and website attempts at the same overall request and time limits.

## 4. Measure the result

1. Freeze a new, independently labeled validation cohort alongside the reusable 1,100-company engineering batch. Include a random company sample and a separate set of verified positive and difficult negative cases for websites, news and jobs. Keep those results separate when reporting coverage.
2. Record an adjudication for each sampled claim. Record exact company, fact value, source evidence and observation time. For each family report correct, incorrect, unsupported and unresolved counts, precision with its denominator, and recall against the positive labels. Keep the local semantic match result separate from factual verification, especially for job expiry and article text.
3. Re-run regression and diagnostic tests, then one live scale comparison with matched configuration. Report completion, requests by phase, time, cost, covered companies, integrity checks and claim-to-record mismatches. Keep source-access failures explicit. Measure refresh using unchanged observations and controlled updates.
4. Prioritize a candidate with zero known material wrong-company publications and zero unresolved mismatches on checked account records. Compare coverage only among candidates that pass those correctness checks. The competition score requires the evaluator's own labels and rules.
