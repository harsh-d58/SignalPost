# Release improvements and push readiness — 12 November 2026

This revision is ready to commit and push as a tested engineering update. Competition qualification and population accuracy are still unmeasured. No commit, push, email or deployment was performed.

## Changes in this pass

- Filing-history audit now checks the exact organisation-keyed official endpoint, retained year list, claimed year, annual-copy URL and reporting period. Explicit wrong-source identities fail the audit. Production extraction rejects mismatched history endpoints and malformed year payloads.
- Website verification and basic extraction finish before optional news/job detail enrichment. Sites recovered by the retry pass receive a second bounded enrichment opportunity. Requests remain charged to the global and phase budgets.
- Same-document JSON-LD publisher references now resolve to one Organization definition. Exact legal identity is still required. Ambiguous definitions and foreign publishers remain blocked. Source references and definition excerpts are retained separately rather than manufacturing nested source text.
- Added filing mutation, deferred-enrichment, request-failure/deadline and publisher-reference tests.
- Added a deterministic review export with source evidence and blank judgments. It refuses to overwrite a reviewer's answers. The local queue contains 189 tasks and no completed labels.
- Updated README test/review commands. Credentials, environments, profiles, snapshots and review tasks remain excluded from Git.

## Verification

The pinned Python 3.12.13 environment installed successfully from `uv.lock` with `uv sync --frozen --group dev`. The final suite passed **267/267 cases**. An earlier 264-case suite also passed under Python 3.13. All 14 frontend resilience tests passed. The console headless check reported no errors or problems. The temporary console was stopped. Refresh replay passed idempotence, typed-change detection and evidence-preserving carry-forward. The whitespace check passed using the repository's CRLF-aware setting.

| Run | Profiles | Requests | Seconds | External API cost | Artifact audit |
|---|---:|---:|---:|---:|---|
| Fresh bulk scale | 1,100/1,100 | 1,920 | 429.3 | $0 | Passed; 48,707 account claims verified; zero invalid/unverified financial claims |
| Fresh direct smoke, Python 3.12 | 100/100 | 607 | 220.1 | $0 | Passed; 4,522 account and 928 filing-history claims verified; zero invalid/unverified financial claims |
| Final publisher-reference check | 2/2 | 31 | 11.5 | $0 | Passed; 63 account and 16 filing-history claims verified |

Compared with the earlier same 1,100-company cohort, websites rose from **22 to 29**, social-profile companies from **9 to 11**, and group coverage from **8 to 78**. Runtime fell from 702.0 to 429.3 seconds while requests rose from 1,742 to 1,920. The retry pass recovered 70 group states and 52 website states; recovered states include explicit non-available outcomes, so 52 is not the number of newly verified sites. Bulk downloads were also faster, so the runtime change cannot be assigned entirely to code.

News-company coverage fell from five to two in the scale run. Inspection found that bare publisher references were being treated as conflicting identities. The subsequent parser fix recovered three dated articles for Gode Tall AS in the focused two-company run. Intergolf still failed the exact-publisher gate and remained unpublished. These focused findings must not be added to the earlier scale total as if one final-code batch produced them. One fewer registry identity was returned in the live scale comparison; live sources changed between observations.

The direct smoke found 11 websites, social profiles for three companies and one article for one company. Jobs remained zero. Approved NAV access is absent, and the existing company-site routes did not find eligible ads in these samples.

## Provenance and limits

The 1,100- and 100-company runs preceded the final publisher-reference correction. Final code was tested by the 267-case suite and the focused two-company live run. The scale/direct operating results therefore characterize the scheduling and evidence revision before that final parser correction. Their original code digests and UTC run IDs are preserved in the machine-readable release manifest. Newline normalization also changed source digests without changing behavior. All runs were based on an uncommitted working tree; a submission commit hash must be obtained after the user commits.

Artifact audits verify retained-source consistency. They do not independently adjudicate every company attribution or establish population precision, recall, F1 or a likely competition score. The review queue is development material, not a blinded test set.

The organizer contract checked on 12 November describes a public 100-company smoke report, code executed on the organizer's shared batch (which can grow to 1,100), and scoring of 50 recall, 30 precision/evidence, 12 synthesis and 8 UX. It says larger precomputed profile files are not themselves submitted or scored. Use the organizer's supplied official batch and limits. [Evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md)

## Remaining work

1. Independently review claims and build a blinded reference set before quoting precision or recall.
2. Secure approved NAV access and validate additional permitted job adapters.
3. Expand cross-host/path and alias support only with exact-entity evidence. Current conservative restrictions can miss legitimate branded pages.
4. Add connection-time DNS pinning/rebinding protection; the current TTL cache and URL checks do not close that transport-level gap.
5. Before final competition submission, rerun the organizer's supplied workload against the committed code. Neither the latest leaderboard nor a name matching the user establishes this repository's official rank.

## Local artifacts and public reports

[Scale metrics](release-scale1100-metrics.json) · [Scale audit](release-scale1100-audit.json) · [Smoke metrics](release-validation100-metrics.json) · [Smoke audit](release-validation100-audit.json) · [Publisher check audit](release-publisher-graph-audit.json) · [Refresh replay](release-refresh-replay.json) · [Release manifest](release-validation-20261112.json)

Private local outputs are `out-release-scale1100`, `out-release-validation100`, `out-release-publisher-graph` and `out-independent-review`. The generated profiles and retained snapshots remain local.
