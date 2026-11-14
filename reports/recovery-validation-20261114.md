# Recovery validation — 14 November 2026

## Result

The known attribution and publication defects from the organizer audit have targeted fixes and regression coverage. This does not establish the required 95% accuracy or a qualifying score: only two of eight wrong-company examples were disclosed, and no independent representative accuracy sample is available.

## Changes and checks

- Website ownership now requires evidence tied to the legal entity; manager/parent pages, agency credits, foreign entities and weak shared-brand social handles are rejected. A verified legal/contact page can be published when the broader homepage remains ambiguous.
- Refresh revokes old company-owned website, description, social and news claims after ownership changes, while temporary fetch failures retain history as stale.
- News requires a substantive article page and a real publication date; utility pages and structured product/job/contact pages are excluded.
- A bounded Greenhouse public-read adapter accepts only explicitly linked boards, exact legal employer names, individual current ads and valid first-published dates. It was fixture-tested; these live cohorts yielded no jobs.
- Bulk download and fallback budgets were tightened. The public sample now contains only selected registry facts and displays a notice that external families are omitted.

Automated validation passed **318 Python tests** (75.38 seconds) and **18 frontend checks**. The generated public UI reported zero errors and zero problems. Named probes reject OTIS India/Worldwide ownership and the bare shared-brand social account while accepting an exact legal-name control. A refresh against the prior wrong OTIS site revoked its website and description; the final canary published neither.

## Measured runs

| Cohort | Valid envelopes | Requests | Runtime | Websites | Social | News | Jobs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fresh 100 | 100/100 | 623 | 243.0 s | 3 | 1 company | 0 | 0 |
| Universe sample 1,100 | 1,100/1,100 | 1,920 | 450.9 s | 20 | 8 companies | 2 items, one company | 0 |
| Final-source universe sample 1,100 | 1,100/1,100 | 1,920 | 288.0 s | 22 | 10 companies | 0 | 0 |

The final-source large run used run ID `run-20261114T170034Z` and code digest `04906cd10003ec517063b9e8857a629eb7d8bcfdcb98c3131210d2cfc81e2efc`. It completed the supplied 1,100 inputs, of which 1,097 resolved to live registry entities. Reported company-family coverage was: financials 99%, leadership 7%, locations 6%, group 1%, websites 2%, social profiles 1%, descriptions 1%, jobs 0%; identity, status, industry and registry activity were 100%. The roles and workplace bulk files timed out; bounded fallback plus tail pass completed without exceeding request or runtime limits. NAV was blocked without `NAV_FEED_TOKEN`. These rates describe emitted availability, not recall: no independently labelled opportunity set exists. The final-source canary was run separately: 100/100 valid, 666 requests, 225.5 seconds, websites 4%, social 2%, descriptions 3%, jobs 0%.

Both runs met their configured execution limits and used **$0 third-party API spend**. The 1,100-company run preceded the final two semantic safeguards; those safeguards were then checked by the complete suite and final named canary. Thus the large-run counts are operational measurements, not a final-source accuracy evaluation. Its two Northstore articles remain unreviewed because retrieval failed; do not treat them as verified news. The 100-company website review is an agent source review, not an independent sample.

Compared with the earlier 1,100-company run (612.2 seconds, 23 websites, 11 social companies, 2 invalid news items and 0 jobs), the new large run was faster and suppressed the known utility-page news pattern. Changes in cohort and code mean the differences do not prove causal recall or precision gains. Website/social counts also fell, which may reflect stricter publication gates and lower coverage.

## Public sample and provenance

The refreshed sample contains 1,000 validated envelopes with registry-only facts. It intentionally excludes website, social, description, news and job claims; it is a browsable sample, not the scored 1,100-company run. See [sample report](public-sample-20261114-report.json) and [manifest](recovery-validation-20261114.json).

The earlier exploratory runs used working-tree digest `8b1278738910b6c3e479c2816ba677d48a51f7f986472e186049b41bb9bf470f`. The final-source canary and 1,100-company batch use digest `04906cd10003ec517063b9e8857a629eb7d8bcfdcb98c3131210d2cfc81e2efc`, based on `11eee14f62de53c42904541f923a39677ce7fc41`. The final commit hash must be recorded after the user commits/pushes.

## Remaining release gates

1. Build an independent, frozen company/fact opportunity pool and report exact-company precision, dated-news/job correctness and recall with denominators and uncertainty.
2. Review the two Northstore news candidates and broaden live job validation; the Greenhouse adapter has fixture evidence only and both cohorts found zero jobs.
3. Obtain or construct negatives for the six undisclosed organizer errors; zero known errors in the named canary does not resolve them.
4. Independently review a sample of the final-source website and social publications; no final-source large-run external claims have been adjudicated yet.
5. Record final branch and full commit hash for the organizer. The old scored commit remains `eaef80456aa6954b40a969892945b4d448e738f7`.

No precision, recall, F1, qualification score or rank is inferred from these operational results.
