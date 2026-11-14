# Signalpost — evidence-backed Norwegian company profiles

Give it Norwegian organisation numbers; it returns one terminal JSON envelope per company with facts from
permitted public sources. Every fact carries its **source URL, retrieval time, reporting period (where relevant),
content SHA-256, claim span and extraction method**. Re-running it is a **refresh** that emits typed changes, and
every run produces a static **showcase site** where each fact is one tap from its proof.

**JBOX companion site:** [Open Signalpost Research](https://build-signalpost-a-read-only-norwegian-c.sites.jboxai.com/). This is the separate public read-only experience; the repository showcase below remains the reproducible project artifact.

**Precision first is the publication goal.** The 14 November recovery adds safeguards for the disclosed
wrong-company cases, refresh revocation and invalid news pages. Broad accuracy and qualification remain
unmeasured; missing financial values are not turned into zero. See the [recovery validation](reports/recovery-validation-20261114.md).

## Organizer result and recovery — 14 November 2026

The organizer scored **eaef804**, at **24.58/100**, rank **100/104**, with **14/22 checked claims correct**.
The newer local HEAD (`11eee14`) was not included in that score. The recovery changes now reject the named
OTIS regional site and revoke it during refresh. The disclosed organizer examples have regressions; six other
wrong-company examples were not supplied. Passing tests do not establish 95% accuracy.

The recovery 1,100-company run completed in 450.9 seconds with 1,920 requests. It emitted 20 websites,
zero jobs and two news candidates that remain unreviewed. A separate fresh 100-company run completed in
243 seconds. The final semantic safeguards passed regression tests and a named canary; no final-source large
run or independent precision/recall estimate exists yet.

Read the [full diagnosis](reports/organizer-diagnosis-20261114.md) and
[recovery plan](docs/dev/organizer-recovery-plan.md). Independent precision/recall remain unknown.
The organizer's entry-specific replacement-commit deadline is **15 November, 09:00 IST**.

## Historical status — 13 November 2026

The latest implementation and measurements are in the [scheduling report](reports/scheduling-improvement-20261113.md); the remaining programme is in [plan.md](plan.md).

- **282 Python tests and 16 frontend resilience tests passed.** Console/showcase interaction checks, source audits and refresh replay also passed.
- The existing scheduler remains the default. `--website-strategy breadth` is an experimental option, pending independent attribution review and matched validation.
- The scale experiment returned **1,100/1,100 valid profiles**, **38 published websites**, **1,920 requests**, **567.9 seconds** and **$0 declared API cost**. These are experimental results, not default-mode performance or measured recall.
- Final state-preservation, timing and default-selection fixes were regression-tested after those live runs; a final committed-code live run remains a submission gate.
- At that checkpoint, independent precision, recall, F1 and official rank were **unmeasured**. See the newer organizer result above; the 82-point plan target is not a forecast.

The scoring contract checked on 12 November uses **50 recall, 30 evidence, 12 synthesis and 8 UX**. Use the organizer's supplied inputs, timestamps and limits. Earlier measurements remain in the [12 November release report](reports/release-readiness-20261112.md) and historical report sections below.

### Evaluator command

```bash
uv run --frozen signalpost run --organisations official-batch.jsonl --registry-snapshot official-registry.jsonl --registry-snapshot-at 2026-11-09T00:00:00Z --evidence-cutoff 2026-11-10T00:00:00Z --bulk-files --workers 8 --job-days 7 --max-requests 2000 --max-minutes 45 --max-cost 10 --out out-official
```

Replace the filenames, observation time, cutoff and limits with Builderr's supplied values. Snapshot rows use Brreg's `organisasjonsnummer` and `navn` fields, in JSONL, JSON array/HAL or CSV, optionally gzip. Without an evaluator snapshot, omit the two registry snapshot options for a live local run. Do not use the public universe as an authoritative current identity snapshot. `--bulk-files` explicitly enables the roles/workplaces inventory route measured on 1,100 companies; omit it for small batches or direct-mode comparison. NAV requires a suitably authorized `NAV_FEED_TOKEN`; without it that source is blocked and company-owned careers discovery continues.

```bash
uv run --frozen python eval/snapshot_audit.py out-official --output reports/snapshot-audit.json
uv run --frozen python eval/metrics.py out-official --output reports/metrics.json
```

Regression and diagnostic tests (both are required in CI):

```bash
uv run --frozen --group dev pytest tests eval/diagnostics -q
uv run --frozen python eval/prepare_review.py out-official --out out-review
# A reviewer fills judgments.jsonl with supported / wrong_entity / wrong_value / unsupported / unresolved.
uv run --frozen python eval/adjudication.py out-official out-review/judgments.jsonl --output reports/adjudication.json
```

The review export contains no generated labels, refuses to overwrite reviewer answers, and is a development review queue. It is not a blinded recall reference set. Filing-history checks verify the exact official source endpoint, listed year, copy URL and reporting period separately from account-record checks.

Snapshot files remain private under the output directory. `--previous` preserves their references on refresh. Full source JSON checks and excerpt-only artifact checks are reported separately. See [source access and retention](SOURCES.md).

---

## Website scheduling experiment (13 November 2026)

The existing scheduler remains the default (`--website-strategy auto` resolves to `legacy`). Use `--website-strategy breadth` to test one complete candidate check per company before alternatives. This changes allocation, not ownership criteria. The 1,100-company experiment published 38 websites versus 29 in the historical baseline at the same 1,920-request ceiling; independent precision/recall are not established, and live-source timing differed. See [the measured comparison and limits](reports/scheduling-improvement-20261113.md).

Runs now include `website-diagnostics.json` and aggregate attempt/completion/budget counts in `run-report.json`. The console and showcase display these as execution counts, not accuracy. Interrupted identity traversal cannot fall through to a weaker acceptance rule. Budget refusal on an alternative preserves an earlier completed ownership decision.

## 1. Quick start

You need **git** and **[uv](https://docs.astral.sh/uv/)**. uv installs the pinned Python (3.12) by itself.

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # once, then reopen PowerShell
git clone https://github.com/harshgitty58/SignalPost.git
cd SignalPost
uv sync --frozen
uv run signalpost run --organisations eval/known-15.jsonl --out out-ui --job-days 7   # ~1 min, 12 well-known companies
start out-ui\site\index.html                                                          # open the showcase
```

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                                       # once
git clone https://github.com/harshgitty58/SignalPost.git && cd SignalPost
uv sync --frozen
uv run signalpost run --organisations eval/known-15.jsonl --out out-ui --job-days 7
open out-ui/site/index.html        # Linux: xdg-open out-ui/site/index.html
```

Your own batch: any JSONL (`{"organisation_number": "923609016"}` per line), JSON list, or plain text with one
number per line works as `--organisations`.

### Optional environment configuration

Registry, Wikidata and company-site discovery need no credentials. The only application credential is
`NAV_FEED_TOKEN`, which must be approved for your deployment. Without it, NAV is reported as `blocked`.
The agent does not automatically load `.env` files. To use the optional example in PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env locally, then start the backend with its environment loaded explicitly.
uv run --frozen --group dev --env-file .env signalpost serve --port 8765
```

Restart the backend after changing the token. Child runs inherit the backend's environment. Keep actual
credentials in `.env` or the process environment; `.env.example` contains only an empty placeholder.
Inputs, output paths, budgets and snapshot timestamps are CLI options. No LLM or search API key is used.

---

## 2. Launch the dashboard (backend + UI)

The dashboard is two pages served by one small local backend: the **live console** (run the agent, tests,
benchmark, evidence check, refresh replay; live terminal, budget meters, per-company "why") and the **showcase**
of any run.

**Start it in your own PowerShell** (this window *is* the backend; keep it open):
```powershell
cd "<path to>\SignalPost"
uv run --frozen --group dev signalpost serve --port 8765
```
It prints the local address of the console; open it in your browser. A run's showcase is served by the same backend
under `/files/out-<name>/site/index.html`. Press **Ctrl+C** in that PowerShell window to stop the backend.
The default console URL is `http://127.0.0.1:8765/`; for the quick-start run, open
`http://127.0.0.1:8765/files/out-ui/site/index.html`. If port 8765 is occupied, choose another `--port`.

### Connecting the UI's terminal to your PowerShell
The showcase home page has a **"Run it locally"** panel with the setup steps and an embedded **PowerShell-style
terminal** underneath:

1. Start the backend in your PowerShell as above.
2. Open the showcase **through the backend** (its `/files/out-<name>/site/index.html` address), not from disk.
   The terminal header turns green: *connected to the local backend*.
3. Press **▶ Run** on a step, or type one of the commands at the `PS …\SignalPost>` prompt. The backend that runs
   in your PowerShell window executes it in your checkout and streams the output into the page.
   **Ctrl+C** (or *Stop*) ends a running job, `cls` clears, `help` lists the commands.

Commands the terminal accepts (everything else is refused, by design; a web page must not be able to run
arbitrary commands on your machine):
```text
uv run signalpost run --organisations eval/<batch>.jsonl --out out-<name> [--job-days N]
uv run --group dev pytest -q
uv run python eval/benchmark.py out-<name>
start out-<name>/site/index.html            (opens that run's showcase in a new tab)
```
Opened straight from disk (`file://`), the panel still shows the steps with copy buttons and tells you how to start
the backend.

---

## 3. Command reference

| Task | Command |
|---|---|
| Install (pinned, exact) | `uv sync --frozen` |
| Run a batch | `uv run signalpost run --organisations <batch> --out out-<name>` |
| Refresh (typed changes vs the last run) | run again into the **same** `--out` (the last run is archived to `out-<name>/history/`) |
| Force a baseline / diff against a specific run | `--fresh` / `--previous out-<other>` |
| Registry only (no websites) | `--no-web` |
| NAV job look-back window | `--job-days 7` (default 60) |
| Local limits (override with evaluator-supplied limits) | `--max-requests 2000 --max-minutes 45 --max-cost 10` |
| Rebuild a run's showcase | `uv run signalpost showcase --envelopes out-x/envelopes.jsonl --report out-x/run-report.json --output out-x/site` |
| Draw a random test batch from a universe file | `uv run signalpost select --universe data/signalpost-universe.jsonl.gz --count 100 --output batch.jsonl` |
| Live console | `uv run --group dev signalpost serve [--port <n>]` |
| Unit tests | `uv run --group dev pytest -q` |
| Benchmark (coverage, 95% Wilson intervals, abstentions) | `uv run python eval/benchmark.py out-x [out-y]` |
| Re-verify evidence at the source (30 samples) | `uv run python eval/verify_evidence.py out-x/envelopes.jsonl --sample 30` |
| Refresh replay (idempotency, typed changes, carry-forward) | `uv run python eval/refresh_replay.py out-x/envelopes.jsonl out-x/refresh-replay.json` |
| Write measured numbers into README/SUBMISSION | `uv run python eval/write_docs.py` |
| Headless UI checks (optional, needs Node) | `npm install --no-save jsdom@24.1.3` → `node eval/ui_check.cjs "<abs path>\out-x\site"` · `node eval/console_check.cjs <console address>` |
| Frontend failure-path checks (same jsdom setup) | `node --test eval/ui_resilience_check.cjs` |

### Manual verification

From the repository root, run the backend and code-only frontend checks:

```powershell
uv run --frozen --group dev pytest tests eval/diagnostics -q -p no:cacheprovider
npm install --no-save --package-lock=false jsdom@24.1.3
node --test eval/ui_resilience_check.cjs
# After the quick-start batch has produced out-ui/envelopes.jsonl:
uv run --frozen signalpost showcase --envelopes out-ui/envelopes.jsonl --report out-ui/run-report.json --output out-ui/site
node eval/ui_check.cjs "$((Get-Location).Path)/out-ui/site"
```

As of 13 November, the Python and diagnostic suites have 282 passing tests; frontend failure-path checks have 16. These checks do not measure
official recall or precision. Run the snapshot audit and metrics commands above against each new batch.

**Outputs** in `out-<name>/`: `envelopes.jsonl` (one per input, input order), `run-report.json` (validation,
coverage, identity gate per source, requests by host and phase, p50/p95, cost), `identity-audit.md`, `website-diagnostics.json`, `site/`
(showcase), `history/` (archived previous runs).

---

## 4. The two UIs

**Showcase** (`out-*/site/index.html`; works from disk, no CDN, no web fonts). Light glass theme (dark on the
toggle), NO/EN interface and summary, 375 px mobile layout, keyboard shortcuts (`/` search, `Esc` close,
`g o/c/h/x/m` switch view, `?` list).
* **Overview:** search with suggestions, a real published fact with its proof, the *Run it locally* terminal, a
  portfolio (availability donut, revenue histogram, industries, counties), a trust panel (evidence completeness,
  abstentions, re-verification, identity-gate decisions, correct rejections), coverage per family with 95%
  Wilson intervals, what changed, run budget.
* **Companies:** sortable table (cards on mobile), filters (family state, legal form, county, website, jobs,
  changed since) kept in the URL, pagination for 1,000+ companies, CSV export.
* **Profile:** org.nr copy, completeness ring, cited summary (English and Norwegian), signals and data checks,
  sections 1–7, account charts (company / group) with exact values, filing history with official PDFs, roles,
  workplaces (optional Kartverket map), jobs, activity, changes with `first_seen` / `times_seen`, unknowns,
  identity audit. Print-friendly.
* **Evidence drawer:** source class, URL, retrieval time, period, method, identity reason, licence, highlighted
  span, full SHA-256 with copy.
* **Compare** (up to four, shareable URL, side-by-side charts; different currencies are never drawn on one
  scale), **Changes** (typed, material/minor) and **Method** (pipeline, gate, states, sources and licences).

**Live console** (`signalpost serve`). Terminal with phase tags, level filters, search and copy; live per-family
coverage bars; budget meters with a requests-over-time sparkline and warning states; per-company "why" dialog with
identity-gate decisions and *Re-run this company*; benchmark tables; evidence re-verification saved for the
showcase; *Diff two runs* (or archived snapshots) using the agent's own change detection.

**Hosted:** the showcase of the committed 1,000-profile run is live at **https://harshgitty58.github.io/SignalPost/**,
rebuilt by `.github/workflows/pages.yml` on every push to `main`.

Design system for both UIs: [`DESIGN.md`](DESIGN.md).

---

## 5. What it collects

| Family | Source | Identity |
|---|---|---|
| identity, status, industry, group membership | Enhetsregisteret (live, 100 orgs/request) | org.nr key |
| annual accounts (company + group, latest years returned by the API, currency, period, audit) + full filing history with links to official copies | Regnskapsregisteret | org.nr key |
| leadership & roles (no birth dates) | Brreg roles API | org.nr key |
| registered workplaces | Brreg sub-units (`overordnetEnhet`) | org.nr key |
| group structure (labelled, never merged) | Brreg konsernstruktur | org.nr key |
| dated activity | Brreg change log (`oppdateringer`, field-level, dated) + verified-site news/RSS | org.nr key / verified site |
| official website | registry site (company or workplace), registry e-mail domain, Wikidata P856 matched by org.nr (P2333), `<name>.no` → **identity gate** | see below |
| social profiles, role e-mail, self-description | outbound links / text on the verified site only | verified site |
| active job postings | approved NAV feed; individual company-site `JobPosting` pages | exact employer/subunit, publication date and active status/deadline |

### Identity gate (website)
Published only with: (1) the exact org.nr printed on the site (not merely among several companies' numbers), or
(2) the company's registered e-mail domain is the site's domain **and** the legal name is in its identity fields,
or (3) legal name in the site's identity fields **and** registry phone/street address on the site (.no), or (4) the
registry (or the Wikidata item carrying the org.nr) declares the site **and** its title/site-name carries the full
legal name. The evidence names which rule and which source proved it. Held back: parked pages, cross-domain
redirects without org.nr, address-like names, holding/investment company names without org.nr, names that are only
a role holder's surname, and sites showing another org.nr (labelled as `related_website` when it is a group entity).

### Budget
Requests are planned per phase; in large batches exact-key official lookups come first. Requests a phase leaves
unused are spent in a final *tail pass* on families that failed only for budget (still within the global cap).

## 6. Models, APIs, cost
* No LLM or paid API. **Recorded external API cost: $0.00 per run**, excluding compute, bandwidth and development tools.
* NAV requires an approved `NAV_FEED_TOKEN`. Without it, the feed is blocked. The public token is available only
  through the explicit `--allow-public-nav-token` private-development option; it is not the official-run default.
* Credential setup is documented in [.env.example](.env.example) and the environment section above.

## 7. Measured results

| Run | Valid profiles | Websites | Requests | Seconds | API cost |
|---|---:|---:|---:|---:|---:|
| Historical default scale | 1,100/1,100 | 29 | 1,920 | 429.3 | $0 |
| Experimental breadth scale | 1,100/1,100 | 38 | 1,920 | 567.9 | $0 |
| Historical default pilot | 100/100 | 23 | 1,137 | 239.6 | $0 |
| Experimental breadth pilot | 100/100 | 23 | 1,099 | 332.8 | $0 |

The scale experiment gained 12 websites and lost three. Live-source conditions and code revisions differed; this is not a controlled recall measurement. Jobs remained blocked without approved NAV access. Cost excludes compute, bandwidth and development tools. See [run hashes, audits and limitations](reports/scheduling-improvement-20261113.md) and its [JSON manifest](reports/scheduling-improvement-20261113.json).

### Historical submission results

The generated block below records the original submission, not the current revision.
<!-- metrics:start -->
- **100 random companies (smoke test)** (dev-rev18f @ `318dd62b4ff9`): 100/100 valid envelopes (validation passed), 899 requests, 4.1 min, $0.00. Coverage: identity 100%, status 100%, industry 100%, financials 100%, leadership 100%, locations 78%, group 5%, website 17%, social_profiles 8%, contact 31%, description 9%, jobs 0%, activity 100%.
- **1,000 random companies (official limits)** (run-1000-rev18b @ `318dd62b4ff9`): 1000/1000 valid envelopes (validation passed), 1920 requests, 2.9 min, $0.00. Coverage: identity 100%, status 100%, industry 100%, financials 100%, leadership 37%, locations 28%, group 5%, website 0%, social_profiles 0%, contact 17%, description 0%, jobs 0%, activity 100%.
<!-- metrics:end -->

Evidence for these numbers is committed in [`reports/`](reports): envelopes (gz), run reports, `benchmark.md`,
`identity-audit.md`, `refresh-replay.json`.

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `uv` is not recognised | Reopen PowerShell after installing uv (or run `$env:Path += ";$HOME\.local\bin"`) |
| The default port is already in use | `uv run --group dev signalpost serve --port <n>` (it prints the new address) |
| The page's terminal says *backend not running* | The page was opened from disk; open it through the backend (`/files/out-<name>/site/index.html`) |
| A job is already running (console) | Wait for it, or press *Stop* / Ctrl+C in the page's terminal |
| You want a clean run instead of a refresh | add `--fresh` |

## 9. Repository layout
```text
src/signalpost/      agent: cli, pipeline, registry, web (identity gate), jobs, refresh, synthesis, budget, http
  showcase/          static site builder + template (overview, companies, profile, compare, changes, method)
  console/           local live console (server + page)
eval/                frozen batches (smoke-100 = dev, val-100, batch-1000, known-15), benchmark, evidence check, refresh replay, UI checks
reports/             committed evidence for the published numbers
tests/               unit tests
docs/dev/            planning, audits and benchmark policy (development history)
```
Full project context (problem, objectives, solution, build, benchmarks): [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).
Challenge requirements and how each is met: [SUBMISSION.md](SUBMISSION.md) · email draft: [SUBMISSION_EMAIL.md](SUBMISSION_EMAIL.md).
Policies: [SOURCES.md](SOURCES.md) (source rights, licences) · [SECURITY.md](SECURITY.md) (outbound URL policy,
console) · [docs/dev/benchmark_plan.md](docs/dev/benchmark_plan.md)
(honest-benchmark rules) · [LICENSE](LICENSE) (MIT).
