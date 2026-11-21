# SignalPost news and jobs plan

The 1,100-company run published zero news items and zero jobs. News logged 32 non-article and 31 unproven-identity rejections. NAV lacked credentials; the empty job-rejection log leaves the company-site and Greenhouse outcomes unclear. [Scale report](reports/bulk-scale-1100-20261120.json)

1. **Freeze the test cases.** Label dated company releases and open vacancies by org number, URL and observation date. Include Aker BP’s missed release, parent-company posts, modified-only dates, careers menus and expired ads.
2. **Trace each candidate.** Record discovery page, detail URL, source, outcome and rejection reason. Track NAV, company careers pages and Greenhouse separately so a blocked feed cannot hide an untested route.
3. **Fix news discovery.** Follow verified newsroom and investor links to individual stories. Require substantive text, an explicit publication date and evidence that the exact company published the item.
4. **Fix job discovery.** Follow verified careers links to individual ads or the existing Greenhouse adapter. Check employer or registered subunit, publication date and open status; recheck closures on refresh.
5. **Test attribution before widening the crawl.** Replay identical pages against both builds. Require the known positives to publish with evidence and the parent, menu, modified-only and expired controls to stay unpublished.
6. **Measure on unseen companies.** Run 100 then 1,100 companies with two workers, at most 2,000 requests and $0 paid API cost per run. Report reviewed precision, company and item recall per family, and requests per supported discovery.

Promote when the labelled holdout gains supported coverage with no new material wrong-company findings. Report recall as unmeasured wherever the reference pool is insufficient. [Evaluation rules](BUILDERR-EVALUATION.md)

## 21 November checkpoint

The discovery changes and six regression cases are implemented. The fresh smoke run produced two source-reviewed Medpoint articles. Aker BP remains a missed positive for both families. Next, isolate ownership proof from the company's own labelled address block, test it against manager and parent-site lookalikes, then replay the release and vacancy through the normal CLI. For vacancies without structured markup, require retained evidence for the employer, publication date, open status and individual application link. [Run results and limitations](reports/news-jobs-validation-20261121.md)

## Ownership and vacancy follow-up

On 21 November, the same five controls went through the normal CLI before and after the change. Websites increased from two to three and individual jobs from zero to one. Both runs produced five valid envelopes at $0. The baseline used 59 requests in 27.4 seconds. The revised run used 57 in 29.4 seconds and passed the retained-evidence audit.

| Control | Revised observation |
| --- | --- |
| Aker BP ASA | The footer's exact legal name, P.O. Box 65 and postcode 1324 matched the registry. The ad identified the employer in the recruiting text, carried a detail-specific publication timestamp on 20 November and showed a 1 December deadline. The application link was retained. The quarterly release is still missing. |
| OTIS AS and Vestsiden Hageby IV Borettslag | Neither the parent nor the manager was published as the target's website. |
| Florø Kjøleservice AS | Found the individual technician page. Its open status was unproven. |
| Olavsborg Kristne Skole | The earlier reviewed ad had an 11 November deadline. The live collector could not establish open status from its current response. The expired-date case is covered offline. |

The full backend and diagnostic suite passed all 367 cases. Replaying the actual Aker claim through refresh with a blocked source retained its history on 1 December and emitted one closed job on 2 December. This was a simulated refresh. The five companies were selected for diagnosis. Measure company and item recall on a separately labelled holdout before estimating competition performance.
