# Ownership and news validation, 19 November 2026

The [frozen inputs and expectations](../eval/cohorts-20261119/manifest.json) cover a random sample of 100 and five selected controls. The random draw used seed 20261119 and excluded 5,024 IDs seen in local uncompressed evaluation, report, and run JSONL files, plus the selected controls. Twelve random inputs have a website in the frozen registry list. Overlap screening was by organisation number. Two previously audited companies were deliberately repeated in the selected cohort. Both live cohorts used one worker.

## Change under test

Baseline code digest `2bb4d854742d3c3184efc1600175616bbb0a24372d5c53ad1bc7f48a3d24d904`. Upgraded digest `babe9cf1016a5a0f9004aea0442b3884c08ac2d09475a0f956d53e6952f6876f`. A name in a longer title or metadata value no longer establishes ownership on its own. An exact normalized identity value or separate ownership evidence can still support publication. This can reduce coverage on legitimate descriptive titles. Article classification now evaluates distinct DOM text and structured article bodies separately so nesting or repeating the same short text across representations cannot meet the length threshold.

The 324 Python tests and diagnostics passed, including three ownership failures and one article failure reproduced on the baseline. All five selected inputs produced valid envelopes before and after, at 66 requests and $0 external API spend per run (53.3 and 44.4 seconds respectively).

| Selected control | Observed before and after |
|---|---|
| Vestsiden Hageby IV Borettslag | Website ambiguous. The manager domain was withheld. |
| OTIS AS | Website ambiguous. Neither the India website nor the global social account was published. |
| Aker BP ASA | Missed the preselected October 29 announcement. Website candidates encountered ambiguous ownership before article extraction. The decision log reports multiple organisation numbers. [Company release](https://akerbp.com/en/borsmelding/third-quarter-2026-results/) |
| Aasen & Farstad AS | Website unavailable. No employee count published. |
| Englund Invest AS | Website blocked. No employee count published. |

The two sparse cases verify missing-value handling only. The Aker case establishes one missed known news opportunity. This five-case development panel has no labelled active vacancy or population precision denominator.

## Fresh random cohort

All 100 inputs produced valid envelopes. The run emitted 8,296 claim rows, of which 7,713 were current published claims and 583 were explicit absence rows in 488.3 seconds using 673 outbound requests, one worker and $0 in external API costs. Website discovery produced candidates for 48 companies and completed checks for all 48. Five companies received websites and one received social profiles. No company received news or a job posting. The NAV feed required credentials. No company with a website candidate went unchecked due to budget.

The snapshot audit checked 7,651 evidence records and found zero missing references, invalid objects or invalid locators. It checked 4,348 account claims and accepted 893 filing-history claims under its date rule. A subsequent comparison found 13 conflicting filing periods. See the [core rules diagnosis](core-rules-diagnosis-20261119.md). These checks measure reproducibility. External precision and recall require independently labelled claims and opportunities. The random cohort was run only on the upgraded code, so it cannot establish a before-and-after coverage change.

The next diagnostic priorities are to trace the Aker BP conflict to the individual identity statements on the page and to add a dated, independently verified open vacancy as a positive control for the careers pipeline. The random cohort leaves both the availability and the detection rate of qualifying vacancies unknown.
