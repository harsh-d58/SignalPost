# News and vacancy discovery, 21 November 2026

## What changed

A verified careers listing can now lead to a single ad before another menu consumes the second fetch. Verified newsroom and investor links can lead to story cards whose slugs omit the word “news”. A visible publication date beside the article heading is eligible evidence. A related story's date and a modification label do not qualify.

Per-company discovery diagnostics record the discovery URL, target URL, source and outcome. The run report aggregates these outcomes across company careers pages, individual ads, Greenhouse, NAV and news. These counts describe route events. A fetched listing can contain zero usable ads.

## Known positive control

Aker BP ASA (989795848) had a [dated quarterly release](https://akerbp.com/en/borsmelding/third-quarter-2026-results/) and an [individual vacancy](https://akerbp.com/available-positions/senior-crisis-management-professional/) linked from its [careers page](https://akerbp.com/ledige-stillinger/). The release was dated 29 October. The vacancy showed an application deadline of 1 December. Labels reflect the observation on 21 November.

The live control published neither item. The registry-declared candidate and the registered email domain both led to an ambiguous ownership decision during site traversal. The run never reached detail extraction. The homepage uses the Aker BP brand and prints the legal name in its postal-address block. The vacancy also lacks structured JobPosting data. Each is a separate recovery problem. The control used 29 of its 80 requests in 21.4 seconds.

## Regressions and measurement

Six new offline cases exercise discovery through a newsroom or careers hub, a dated story with an unmarked slug, an updated-only story, a related story's date, an open vacancy, a different employer and an expired vacancy. The fixtures use a fixed clock and assert the fetched URLs and published claims.

The random smoke and scale inputs were sampled with seed 20261121 from 411,160 rows after excluding 5,128 prior company numbers. The two live runs used two workers each, in sequence, with breadth scheduling and a limit of 2,000 requests, 45 minutes and zero paid API cost per run. Bulk files were enabled for scale. Exact known hosts are isolated across splits. Undiscovered shared parent domains may remain. These cohorts have no independently checked inventory of company articles or vacancies.

## Reviewed smoke findings

The 100-company run produced 100 valid outputs in 328.3 seconds using 595 requests. Of 36 companies with attempted website candidates, three passed ownership checks. Those three exposed no eligible careers or Greenhouse links. NAV required credentials. Four news detail or index fetches yielded two stories, both from MEDPOINT AS (828486462). The evidence integrity audit passed.

| Source item | Published | Other dates on the page |
| --- | --- | --- |
| [Medpoint vaccine availability](https://medpoint.no/siste-nytt/influensavaksine-hosten-2026-hvem-nar-og-hva-koster-det/) | 6 October 2026 | Updated 26 October |
| [Medpoint notice on consultation tariffs](https://medpoint.no/siste-nytt/endringer-i-fastlegeordningen/) | 6 August 2026 | Effective 1 July and updated 26 October |

Both public source pages support the reported titles and publication dates and identify Medpoint AS. That gives two supported news items out of two reviewed in smoke, from one publisher. With zero published vacancies, job precision has no denominator. The Aker control and Medpoint review were selected for diagnosis, so combining them into a population recall estimate would be misleading.

## Scale and release decision

The 1,100-company run emitted 1,100 valid envelopes in 641.3 seconds, used 1,920 requests and incurred $0 in external API costs. The retained-evidence audit passed. Of 1,091 resolved companies, 150 received a website attempt and 18 had a website published. Eleven verified sites exposed no eligible careers link. Six careers fetches succeeded, two failed and one hit the budget. None produced a vacancy. All 18 sites lacked an eligible Greenhouse board link. NAV remained unavailable.

The scale run published one [Alpha AI blog article](https://www.alphaai.no/blog/2026/04/16/hva-er-kunstig-intelligens-og-hvordan-endrer-det-fremtidens-naeringsliv/). The retained article fragment shows the headline, explicit publication timestamp on 16 April 2026 and a publisher reference resolving to ALPHA AI AS. The retained contact excerpt gives org number 934802519. The independent browser fetch returned a cache miss. This review establishes support in captured evidence only.

All 356 offline tests passed. Smoke ran before the final change that tied visible date labels to the heading block and corrected feed/sitemap provenance. Scale and the two-company replay used the final build. The replay reproduced both Medpoint URLs and both Aker omissions. The frozen cohorts differ from yesterday's, so the change in counts cannot quantify an improvement in recall.

Keep the diagnostics and regression coverage. Defer a competition promotion claim until an independent labelled set demonstrates gains in company and item recall. First inspect the six successful careers fetches, distinguish menus from individual ads lacking markup, then test scoped employer evidence on confirmed positives alongside parent-company counterexamples. [Smoke run](news-jobs-smoke-20261121.json) · [Scale run](news-jobs-scale-20261121.json) · [Frozen inputs](../eval/cohorts-20261121/manifest.json)
