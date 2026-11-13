# Submission and push checklist — 13 November 2026

Repository: https://github.com/harshgitty58/SignalPost. Current local branch: `main`.

This revision is ready for the user to review and push as an engineering update. It is **not a measured top-three entry or an independently qualified release**. Before emailing a competition revision, freeze the exact commit and complete the final committed-code run and ownership review below.

## What this update contains

- Interrupted website identity traversal now stays unpublished instead of falling through to weaker evidence.
- Existing scheduling remains the default (`auto` resolves to `legacy`). Breadth-first candidate rounds are available explicitly with `--website-strategy breadth` for experiments.
- Website attempt/completion/budget diagnostics are included in reports and displayed by both frontend surfaces. Older reports remain compatible.
- A fresh 100-company research pilot, corpus/probe/comparison tools, regression tests and the detailed improvement plan are included. Private generated inputs, snapshots and review tasks remain local.

Verification: **282 Python tests and 16 frontend tests passed**; console/showcase interaction checks, source audits and refresh replay passed. See [implementation report](reports/scheduling-improvement-20261113.md) and [run manifest](reports/scheduling-improvement-20261113.json). The live experiments preceded the final state/timing/default corrections; those corrections have regression coverage, not a new final-code scale measurement.

## Reported performance and source declarations

| Run | Profiles | Websites | Requests | Seconds | Declared API cost |
|---|---:|---:|---:|---:|---:|
| Historical default scale | 1,100/1,100 | 29 | 1,920 | 429.3 | $0 |
| Experimental breadth scale | 1,100/1,100 | 38 | 1,920 | 567.9 | $0 |
| Historical default pilot | 100/100 | 23 | 1,137 | 239.6 | $0 |
| Experimental breadth pilot | 100/100 | 23 | 1,099 | 332.8 | $0 |

These live comparisons do not establish precision or recall. Exact attribution must be independently reviewed. Do not describe the 38-website result as the default scheduler's result. NAV was blocked without an approved token. No LLM or paid API is used; measured external API cost is $0, excluding compute, bandwidth and development tools.

Sources: Brønnøysundregistrene APIs and declared bulk records, authorized NAV access when configured, Wikidata for discovery candidates only, and permitted company-owned pages with robots checks. See [SOURCES.md](SOURCES.md), [SECURITY.md](SECURITY.md) and [.env.example](.env.example). Connection-time DNS protection remains an open item in the improvement plan; do not claim all transport risks are closed.

## Push this engineering update

Run from the repository root. Review the diff before staging. Do not switch branches or force-push. No push has been performed by the assistant.

```powershell
git status --short
git diff --check
git diff --stat

git add README.md SUBMISSION.md SUBMISSION_EMAIL.md PROJECT_CONTEXT.md .env.example plan.md
git add docs/dev/metrics-improvement-plan.md docs/dev/deep-website-search-plan.md
git add src/signalpost/cli.py src/signalpost/pipeline.py src/signalpost/web.py
git add src/signalpost/console/console.html src/signalpost/console/server.py src/signalpost/showcase/template.html
git add eval/build_website_corpus.py eval/website_modes.py eval/website_metrics.py eval/ui_resilience_check.cjs
git add tests/test_website_corpus.py tests/test_website_scheduling.py
git add reports/website-pilot-20261112.md reports/website-pilot-20261112.json reports/scheduling-improvement-20261113.md reports/scheduling-improvement-20261113.json

git diff --cached --stat
git diff --cached --check
git commit -m "Improve website verification diagnostics and add breadth scheduling experiment"
git push origin main
git rev-parse HEAD
```

If normal whitespace checking flags existing Windows line endings, use `git -c core.whitespace=cr-at-eol diff --check` (and `--cached` after staging). Resolve actual whitespace errors rather than suppressing them.

`.gitignore` already excludes `.env`, local environments/caches, `out-*`, snapshots, downloaded data, logs, node_modules and the generated ZIP. `.env.example` contains no token. Explicit staging above avoids adding unrelated scratch files. Inspect staged content for secrets before committing.

A push touching the showcase template can trigger the existing Pages workflow. It rebuilds the **historical committed 1,000-profile sample**, not the private latest pilot. Check Actions after pushing; do not assume a successful deployment or a green clean-machine job before it completes.

## Before emailing a competition revision

- Confirm the published deadline and remaining revision slots against the organizer's current instructions and submission acknowledgments. The contract checked on 12 November lists 16 November 2026 and four revisions after the initial submission.
- Use a clean checkout of the pushed hash, pinned dependencies and the declared command.
- Run the final committed code on the supplied or newly frozen inputs. Review ownership of published websites/social/news/jobs and audit source support.
- Produce a public 100-company smoke report from that revision. Existing reports are supporting historical evidence, not a new exact-commit run.
- Preserve exactly one terminal envelope per input, source dates, hashes, reporting periods, explicit missing/blocked states and refresh evidence.
- Keep the submitted strategy explicit. Use `legacy` unless independent validation has justified promoting `breadth`.
- Supply repository link, exact 40-character commit hash, command, model/API details and expected external API costs. Larger precomputed profile files are not the current official scoring input.
- Update [the email draft](SUBMISSION_EMAIL.md) with the actual hash and final report. The user's supplied contact is Harsh Dhavane, harshdhavane06@gmail.com.

## Evaluator command

Install with `uv sync --frozen`, then use this single run command. Replace the example files, timestamps and resource limits with the organizer's supplied values:

```bash
uv run --frozen signalpost run --organisations official-batch.jsonl --registry-snapshot official-registry.jsonl --registry-snapshot-at 2026-11-09T00:00:00Z --evidence-cutoff 2026-11-10T00:00:00Z --bulk-files --website-strategy legacy --workers 8 --job-days 7 --max-requests 2000 --max-minutes 45 --max-cost 10 --out out-official
```

For live local testing without a supplied identity snapshot, omit both registry snapshot arguments. Do not treat an old universe download as a current authoritative anchor. Optional NAV credentials must be supplied securely and reproducibly; the agent does not read `.env` automatically.

## Local checks

```powershell
uv run --frozen --group dev pytest tests eval/diagnostics -q -p no:cacheprovider --basetemp=.test-tmp/prepush-next
npm install --no-save --package-lock=false jsdom@24.1.3
node --test eval/ui_resilience_check.cjs
# After creating a fresh run:
uv run --frozen python eval/snapshot_audit.py out-official --output out-official/source-audit.json
uv run --frozen python eval/refresh_replay.py out-official/envelopes.jsonl out-official/refresh-replay.json
```

Generate an archive only after committing: `git archive --format=zip -o signalpost-code.zip HEAD`. The archive does not include uncommitted work. No email or submission is sent by these commands.
