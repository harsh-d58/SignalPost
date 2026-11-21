# SignalPost bulk upgrade plan

Baseline: both registry archives timed out; only 65 of 1,096 resolved companies received a website check. [Scale report](reports/core-fixes-checkpoint-20261119.md)

1. Log bytes received, last progress time and failure stage for each archive.
2. Start website checks during downloads; cap direct fallback separately for roles and workplaces.
3. Test slow, stalled and truncated archives; report missing rows as unknown after an incomplete download.
4. Replay `breadth` and `legacy` on identical responses; compare verified companies per 100 requests.
5. Test site owner, article publisher and employer separately against parent-company lookalikes.
6. Refresh from a dated baseline; deduplicate Brreg’s inclusive update ID and save the cursor after evidence is stored. [Brreg API](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/)
7. Run 100 then 1,100 companies with two workers, 2,000 requests and $0 API spend per run.

Release when coverage improves, every input returns a result, evidence checks pass and review finds no new material ownership errors. [Builderr evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md)

[Implementation and measured results](reports/bulk-upgrade-20261120.md)
