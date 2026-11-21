# Signalpost correction and validation checkpoint

Working tree on top of `6a87ab71d7c0c24af0017851630d6f6ac4631f52`. Keep existing changes. The owner will commit and push manually. See [diagnosis](core-rules-diagnosis-20261119.md) for the baseline.

## Implemented

- Website attribution checks explicit operator metadata for conflict. A registry URL plus a page title alone is insufficient. A verified company subpage cannot confer its surrounding homepage brand. Contact-based matches retain separate source excerpts and link the registry claim when present.
- Filing-history claims now publish the source year and official copy without supplying calendar boundaries. The auditor rejects unsupported periods. Refresh recognises the removal of legacy calendar boundaries as a parser correction. Cutoffs reject filing years later than the cutoff year.
- Monetary claims require supported account scope, currency and a valid source period. Audit status requires explicit boolean flags. The audit tool now rejects unsupported scope and audit-status transformations.
- Registry-only opportunities cannot enable a weighted external recall score. Registry events are excluded from the news denominator. The operational report now distinguishes current publications from raw claim rows.

## Validation ledger

The live run in `out-cohorts-20261119/corrected100` started before the final ownership and account-period refinements. It tests an intermediate build. The source digest in its report identifies that build. Use the completed final-build results below when assessing release readiness.

The full test suite exposed another execution defect. With an evaluator cutoff, valid date-only reporting periods reached a parser that required timezone-aware timestamps. The runner now compares calendar dates at day precision and observation timestamps at instant precision. Regression cases cover same-day inclusion, future periods and year-only filings.

The intermediate live run returned 100 valid envelopes in 489.5 seconds, with 678 requests and $0 API cost. The corrected auditor accepted all 893 year-only filing claims and rejected all 893 legacy claims carrying unsupported exact dates on the original comparison run. Both runs had zero invalid account claims. The intermediate run published two websites versus five previously. AKTIVTMED AS and TORSTA AS lacked sufficient name/contact proof under the new check. GS SEAT AS was ambiguous due to multiple numbers. These were live observations at different times. Both runs published zero news and zero jobs.

All 342 Python tests and 18 frontend regressions passed. The registry-only public sample contains zero year-history claims carrying unsupported calendar periods. The historical smoke artifact still has 1,018 such rows and should not be presented as output from the corrected build.

## Final-build scale result, November 20 IST

All 1,100 inputs returned valid envelopes in 560.1 seconds, with 1,920 requests and $0 API spend. Two workers processed the batch. The snapshot audit passed with 48,658 account claims verified and zero invalid locators. No filing-history claims were emitted at this scale. Replaying all 1,100 through the refresh comparison produced zero changes. The parent/customer reproduction withheld the website, and the missing-scope financial fixture emitted no claims.

The run published 16 websites, social profiles for five companies, zero company news and zero jobs. Both bulk registry downloads exhausted their time budgets. Website diagnostics recorded 65 completed company checks and 1,031 resolved companies unattempted due to budget. Four inputs did not resolve in the registry. Fixes to attribution and filing evidence have test coverage. External recall remains a release concern.

Raw artifacts are local under `out-cohorts-20261119/final1100`. The final-build 100-company smoke uses the same frozen random cohort as the before/after comparison.

## Final-build smoke result

The [100-company smoke report](smoke-100-20261120.json) and scale report have the same source digest, `1a7b3a27109c04a40ea05b97eb57609526d246fca70569e25e2777a9a4b8d3bb`. All 100 inputs returned valid envelopes in 288.3 seconds, using two workers, 672 requests and $0. The snapshot audit passed for 4,348 account claims and all 893 year-only filing claims. None carried unsupported calendar dates. Replay produced zero changes. Two companies had websites, one had social profiles, and none had published news or jobs. Independent claim precision, pooled recall and Builderr qualification remain unmeasured for this build.
