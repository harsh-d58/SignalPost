# JBOX build checkpoint

Project created: https://jboxai.com/project/yxtaf07yxltrm6awyz013fxw/

Status: public JBOX site is available at [build-signalpost-a-read-only-norwegian-c.sites.jboxai.com](https://build-signalpost-a-read-only-norwegian-c.sites.jboxai.com/). The repo links to it as the companion read-only experience. The repository does not contain JBOX's generated source or deployment proof; no claim is made here about specific live features beyond the site's stated read-only purpose. No invented company data is authorized.

Local data export: `out-jbox/data/index.json` and `out-jbox/data/companies/*.json`.
Source: `out-website-pilot-baseline/envelopes.jsonl`, observed 12 November 2026 UTC.
Export: 100 companies, 2,743 selected official-registry claims and 2,743 evidence entries; approximately 2.5 MB uncompressed.

The exporter restricts source class/license/host and checks locator organisation number. It excludes stale values, contact/role fields, external-source claims, raw snapshots and debugging data. This is a publication filter, not independent reference adjudication. The published JBOX site's data linkage and exact export revision should be recorded when confirmed.

Reproduce with a fresh output directory:

```powershell
uv run --frozen python eval/export_jbox_data.py out-website-pilot-baseline/envelopes.jsonl --out out-jbox-next/data
uv run --frozen --group dev pytest tests/test_jbox_export.py -q
```

Next: confirm the connected data export revision and test search, compare and evidence flows on laptop and phone. Bonus deadline eligibility remains unconfirmed. The user will push repository changes manually.
