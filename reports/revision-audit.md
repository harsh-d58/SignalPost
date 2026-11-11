# SignalPost revision audit

The revised agent completed local runs on independently sampled public batches at both 100 and 1,000 companies. Results below are from working-tree builds. Record the exact release commit and regenerate the public smoke report from that checkout before submitting the revision.

| Live batch | Valid envelopes | Requests | Elapsed | External cost |
|---|---:|---:|---:|---:|
| [100 companies](revision-smoke-100-run-report.json) | 100/100 | 660 | 3m 38s | $0 |
| [1,000 companies](revision-scale-1000-run-report.json) | 1,000/1,000 | 1,920 | 1m 32s | $0 |

The large run found 26 verified website claims, 18 social accounts across nine companies, and two individual vacancies. It also emitted 16 news rows. Inspection found two duplicates caused by equivalent encoded and unencoded URL paths. The final code normalizes these paths and has a regression test. The live table records the original measured runs.

Large-batch coverage remains constrained by requests. The 1,000-company run found accounts for 988 companies, roles for 175 and workplaces for 142. Only 26 companies had a verified website. The [technical plan](../docs/dev/rank-up-plan.md) prioritizes recovering those registry and website opportunities with bulk sources and request allocation.

## Problems found and fixed

| Before | Revision |
|---|---|
| A group homepage, conflicting footer IDs or a redirected contact page could establish website identity incorrectly. | Require company-specific ownership evidence, keep the proven page URL, and hold back conflicting identities. |
| Parent, agency or theme handles could pass on a footer link, `sameAs` or loose name match. | Require a matching company handle and keep exact-entity website verification upstream. |
| News links could be menu text, products or modification-only dates. | Check article type, detail URL, company scope and explicit publication date. Normalize equivalent encoded paths before counting an item. |
| General careers pages and group jobs could resemble single-company vacancies. | Check current status, individual ad identity and exact employer before publication. |
| Partial vacancy scans could create false closure changes. | Mark coverage incomplete and keep unconfirmed prior facts stale. Expiry can still close a dated ad. |
| Some incomplete evidence and mismatched official records could pass through. | Require evidence excerpts and extraction methods, retain exact official identifiers, and keep missing finance values distinct from zero. |

## Verification

- 131 Python tests passed in a clean Python 3.12 environment, including mocked 100-, 1,000- and 1,100-company runs and failure handling.
- The live source recheck found 100 of 100 sampled excerpts from the 1,000-company output. This sample verifies excerpt availability. The publication fixtures exercise attribution separately.
- The refresh replay passed unchanged-snapshot, typed-change and source-failure cases. The generated showcase passed search, filters, comparison, evidence drawer and keyboard checks. The local console passed its browser-flow harness.
- An additional 100-company attempt spanned a workspace interruption and exceeded its configured wall-time limit. The completed rerun above is the valid smoke measurement.

## Reproduce

```sh
uv run --frozen signalpost run --organisations eval/audit-fresh-100.jsonl --out out-audit-smoke --job-days 7
uv run --frozen signalpost run --organisations eval/audit-fresh-1000.jsonl --out out-audit-scale --job-days 7
uv run --frozen pytest -q
uv run --frozen python eval/verify_evidence.py out-audit-scale/envelopes.jsonl --sample 100
uv run --frozen python eval/refresh_replay.py out-audit-scale/envelopes.jsonl out-audit-scale/refresh-replay.json
```

The local 1,000-profile output is in `out-audit-verified1000/envelopes.jsonl`. Its generated showcase is in `out-audit-verified1000/site/index.html`. The earlier tracked 1,000-profile archive remains available for the original submission.
