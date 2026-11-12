# Submission pack — Builderr "Signalpost" challenge

Repository: https://github.com/harshgitty58/SignalPost (branch `main`) · The email to send: [SUBMISSION_EMAIL.md](SUBMISSION_EMAIL.md)

## Current scoring and revision

The current working-tree revision is documented in [release verification and measured metrics](reports/release-readiness-20261112.md). Use the evaluator command in [README](README.md), including `--bulk-files` for large batches. NAV requires a permitted credential and is blocked by default without one. Optional environment setup is documented in [.env.example](.env.example). Freeze an exact new commit before sending a revision.

Builderr's published scoring weights are 50 for recall and coverage, 30 for precision and evidence, 12 for synthesis, and 8 for UX. Qualification requires 65/100 overall and passing the integrity and execution checks. Builderr supplies the official batches. Submit a public 100-company smoke result or report, the exact revision commit, a reproducible command, and source and cost details. The organizer lists November 16, 2026 as the revision deadline. [Scoring](https://builderr.ai/challenges/signalpost#scoring) · [Evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md)

See [the release report](reports/release-readiness-20261112.md) for current checks and results. The generated metrics in section 3 are explicitly historical.

## 1. Requirements checklist

Local checks as of 12 November 2026. Official recall, precision, qualification and rank remain unmeasured.

### What to build
| Requirement | Status | Where it is shown |
|---|---|---|
| Take a Norwegian organisation number, search permitted public sources | ✅ | `uv run signalpost run --organisations <batch> --out out/`; sources and licences in [SOURCES.md](SOURCES.md) |
| Return company facts, source links and dates | ✅ | every claim has source URL, retrieval time, reporting period (where relevant), content SHA-256, claim span, extraction method; `reports/*-envelopes.jsonl.gz` |
| Each fact belongs to the right company | Audit required | exact org.nr keys and website identity gates are implemented; exact-company fixtures and source audits pass, but independent population precision is unmeasured |
| Keep profiles current | ✅ | re-running into the same output folder is a refresh: typed, material/minor changes, `first_seen` / `last_seen` / `times_seen`, unreadable sources carried forward; [reports/refresh-replay.json](reports/refresh-replay.json) = PASS |

### What to submit
| Requirement | Status | Where it is shown |
|---|---|---|
| Public 100-company smoke result or report | ✅ locally | `reports/release-validation100-metrics.json`; the existing 1,000-profile Pages sample is historical demonstration data, not the official scoring input |
| Repository link | ✅ | https://github.com/harshgitty58/SignalPost |
| Exact commit hash | ✅ at send time | `git rev-parse HEAD` after `git push origin main` (§2) |
| One command to run it | ✅ | `uv sync --frozen` then `uv run signalpost run --organisations <batch.jsonl> --out out/` |
| Model / API details | ✅ | no LLM; Brønnøysundregistrene open APIs (NLOD 2.0), NAV with approved `NAV_FEED_TOKEN` or blocked, Wikidata SPARQL (CC0, candidates only), permitted company-owned pages |
| Expected run costs | Measured | **$0.00** external API cost for the recorded connector set; excludes compute, bandwidth and development tools |

### How it is tested and scored
| Item | Status | Evidence |
|---|---|---|
| Execution limits | Passed locally | use evaluator-supplied limits; recorded bulk run returned 1,100 results in 429.3 seconds using 1,920 requests and $0 external API cost |
| Exactly one terminal envelope per input | Passed locally | tested up to 1,100 inputs including source failures; exhausted runs exit unsuccessfully even when envelopes are emitted |
| Clean-machine install | ✅ | `uv sync --frozen` from a fresh clone; GitHub Actions `clean-machine` workflow runs tests + a live smoke on every push |
| Recall and coverage (50) | Unmeasured officially | latest scale run: 29 websites, social profiles for 11 companies, news for 2 companies and no jobs; the final publisher-reference correction has separate focused validation |
| Precision, exact identity and evidence (30) | Unmeasured officially | latest scale audit verified 48,707 account claims; direct smoke verified 4,522 account and 928 history claims; independent factual precision remains unknown |
| Refresh requirements | Passed local replay | unchanged-source replay produced zero false changes; controlled changes, stale carry-forward and prior evidence tested |
| Useful explanations (12) | Implemented, unscored | cited deterministic English/Norwegian summaries, signals, changes and unknowns |
| UX (8) | Implemented, unscored | find, compare and verify flows; 14 frontend failure-path tests and interaction checks on current and legacy datasets |
| Qualify: ≥65/100 and valid official run | Unknown until scored | no separate component threshold in the current published contract |
| No material wrong-company publication or fabricated financial value | Release gate | strict identity and financial publication tests; no claim of independently measured population precision |
| JBOX bonus | — | not claimed (the agent was not built with JBOX) |

## 2. Send it
```powershell
git checkout main
git push origin main
git rev-parse HEAD                                   # the exact commit hash
git archive --format=zip -o signalpost-code.zip HEAD # the code at that commit (about 9 MB), to attach
```
Check that `https://github.com/harshgitty58/SignalPost/commit/<sha>` opens and the `clean-machine` workflow is green,
then send [SUBMISSION_EMAIL.md](SUBMISSION_EMAIL.md) to **submit@builderr.ai** with the hash filled in and the zip
attached. Form field: `https://github.com/harshgitty58/SignalPost/commit/<40-char-sha>`.

## 3. Historical submission metrics (generated by `eval/write_docs.py`)
<!-- metrics:start -->
- **100 random companies (smoke test)** (dev-rev18f @ `318dd62b4ff9`): 100/100 valid envelopes (validation passed), 899 requests, 4.1 min, $0.00. Coverage: identity 100%, status 100%, industry 100%, financials 100%, leadership 100%, locations 78%, group 5%, website 17%, social_profiles 8%, contact 31%, description 9%, jobs 0%, activity 100%.
- **1,000 random companies (official limits)** (run-1000-rev18b @ `318dd62b4ff9`): 1000/1000 valid envelopes (validation passed), 1920 requests, 2.9 min, $0.00. Coverage: identity 100%, status 100%, industry 100%, financials 100%, leadership 37%, locations 28%, group 5%, website 0%, social_profiles 0%, contact 17%, description 0%, jobs 0%, activity 100%.
<!-- metrics:end -->
1,000 profiles: `reports/run-1000-envelopes.jsonl.gz` (+ run report) · Smoke test: `reports/smoke-100-run-report.json` +
`reports/smoke-100-envelopes.jsonl.gz` · Benchmark with 95% intervals: `reports/benchmark.md` · Identity audit:
`reports/identity-audit.md` · Refresh proof: `reports/refresh-replay.json` · Source rights: [SOURCES.md](SOURCES.md) ·
Security / URL policy: [SECURITY.md](SECURITY.md)

## 4. Before every revision
```bash
uv run --frozen --group dev pytest tests eval/diagnostics -q -p no:cacheprovider
node --test eval/ui_resilience_check.cjs
uv run --frozen signalpost run --organisations eval/rankup/smoke-100.jsonl --out out-check --job-days 7
uv run --frozen python eval/refresh_replay.py out-check/envelopes.jsonl out-check/refresh-replay.json
uv run --frozen python eval/snapshot_audit.py out-check --output out-check/snapshot-audit.json
uv run --frozen python eval/metrics.py out-check --output out-check/metrics.json
uv run --frozen python eval/verify_evidence.py out-check/envelopes.jsonl --sample 30
# review out-check/identity-audit.md: every published website must be the exact company
```
Install jsdom for the frontend check using the README instructions. Existing smoke/scale cohorts are now
development data; freeze a new uninspected cohort before claiming a blind release check. The organizer accepts
up to four revisions after the initial submission. Send the exact commit hash for each revision.
