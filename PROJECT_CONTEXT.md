# Signalpost — full project context

One document that explains the problem, what we set out to achieve, the solution we chose, how it is built, and how
it performs. All numbers come from the committed [`reports/`](reports) folder (generated from real runs). Nothing
here is estimated.

---

## 1. Problem statement

The Builderr challenge **"Signalpost: Build an agent that finds company information"** asks for an agent that is
given a **Norwegian organisation number**, searches **permitted public sources**, and returns **company facts, source
links and dates**. Every fact must **belong to the right company**, and profiles must be **kept current**.

How it is tested:
- Every agent receives the **same 100 random companies each day**.
- Score out of 100:

| Area | Points |
|---|---|
| Find useful information (coverage, compared with a pooled set built from submissions and Builderr crawlers) | 35 |
| Match it correctly with evidence (precision and evidence quality) | 30 |
| Update correctly (refresh) | 20 |
| Give useful explanations (synthesis) | 10 |
| Make it easy to use (UX) | 5 |

- **To qualify:** at least 65/100 overall and 21/35 coverage, plus all published accuracy, evidence and execution
  requirements.
- **Disqualifying errors:** a single material **wrong-company publication** or **fabricated financial value**.
- **Daily limits:** 45 minutes, 2,000 outbound requests, $10 in declared external API costs.

What must be submitted: at least 1,000 company profiles, the repository link, the exact commit hash, one command to
run it, model/API details, and expected run costs.

Why it is hard:
- An organisation number is only a key. The useful facts are spread over several registries and the open web.
- The web is noisy. Many companies share names, use brand names, sit in groups, or have parked or unrelated domains.
- The population is mostly small companies: about **85% have no employees** and only about **11% list a website**,
  so web-based facts are sparse by nature.
- Because one wrong-company fact disqualifies the entry, a confident guess is worse than an honest "unknown".

---

## 2. Objectives

From the scoring:
1. **Coverage:** publish as many verifiable facts per company as the sources allow, within the daily limits.
2. **Precision and evidence:** every fact is tied to the exact legal entity and carries the proof needed to check it.
3. **Updates:** a re-run detects real changes, never invents them, and does not lose facts when a source is
   temporarily unreadable.
4. **Explanations:** a short, readable summary that cites its facts and states what is unknown and why.
5. **Ease of use:** find, compare and verify on desktop and mobile.

Our own rules on top of that:
- **Precision first.** When identity cannot be proven, the answer is `ambiguous` or `not_available`, never a guess.
- **Missing is never zero.** Every field family ends in one of six explicit states with a reason.
- **Honest benchmarks.** Frozen test batches, no tuning on official batches, abstentions reported, every published
  number reproducible from `reports/` ([docs/dev/benchmark_plan.md](docs/dev/benchmark_plan.md)).
- **Cheap and reproducible.** No paid APIs, no keys, the same input gives the same output, clean install from a pinned
  lockfile.

---

## 3. Proposed solution

**Signalpost is a deterministic, registry-anchored agent.** It starts from the one thing that is certain, the
organisation number, and only widens to softer sources when it can prove identity.

Key decisions and why:

| Decision | Why |
|---|---|
| Anchor on Brønnøysundregistrene exact-key APIs | Official, open (NLOD 2.0), keyed by org. number, so zero identity risk for most facts |
| Web data only behind an **identity gate** | The web is where wrong-company errors happen; the gate states which rule proved each site |
| Jobs only when the ad's employer org. number matches | NAV ads carry the employer's number, so matching is exact rather than by name |
| **No LLM** | A language model can produce exactly the two disqualifying errors (wrong company, invented numbers). Rules plus evidence cannot; it also keeps the cost at $0 and the output reproducible |
| Six availability states per family | Makes abstention visible and scoreable instead of silent |
| Refresh by diffing stable claim keys | Typed, explainable changes; idempotent re-runs; carry-forward when a source fails |
| A static showcase per run | Judges and users can verify any fact in one tap, offline, without a server |

### The data contract
For each input number the agent emits **exactly one terminal JSON envelope** containing:
- **claims** (facts), each with family, field, value, unit, reporting period, effective date, `first_seen` /
  `last_seen` / `times_seen`, and evidence ids;
- **evidence** records: source URL, source class, retrieval time, reporting period, **content SHA-256**, the **claim
  span** (the exact source text), extraction method, licence and identity reason;
- **availability** per field family (13 families) in one of six states: `available`, `not_available`, `ambiguous`,
  `blocked`, `failed`, `not_applicable`, each with a reason;
- **changes** since the previous run (typed, material or minor);
- a **brief** (cited summary in English and Norwegian, signals, data checks, unknowns), the identity-audit list of
  candidates that were *not* published, run metadata and per-company operations (requests, time, cost).

The 13 field families: legal identity, registry status, industry, annual accounts, leadership and roles, registered
workplaces, group structure, official website, company-owned profiles, contact, self-description, job postings,
dated activity.

---

## 4. How it is built

**Stack:** Python 3.12, managed with uv and a frozen lockfile. Runtime dependencies: `httpx`, `lxml`, `jinja2`.
About 6,900 lines across the agent, the two UIs, tests and evaluation tools. MIT licence.

### 4.1 Pipeline (one run)
1. **Budget plan.** Requests are reserved per phase before any work starts, so no source can starve another. Large
   batches put exact-key official lookups first. Defaults enforce the official limits (45 min, 2,000 requests, $10),
   with a safety margin.
2. **Registry anchor.** Live Enhetsregisteret lookup, 100 companies per request: legal name, form, addresses,
   municipality, industry, status flags, employees, registry-declared website, e-mail, phone.
3. **Official facts by exact key.** Annual accounts (company and group, with currency and period), the full filing
   history with links to the official PDF copies (small batches; the endpoint is paced), roles (no birth dates),
   registered workplaces, group structure, and the registry's dated change log as activity.
4. **Website discovery and the identity gate.** Candidates come from the registry-declared site (company or
   workplace), the registry e-mail domain, Wikidata (matched by org. number, P2333 → P856) and name-based `.no`
   domains. A site is published only if one of four rules holds:
   1. the exact org. number is printed on the site (and not merely among several companies' numbers);
   2. the registered e-mail domain is the site's domain and the legal name is in its identity fields;
   3. the legal name is in its identity fields and the registry phone or street address appears on the site;
   4. the registry (or the Wikidata item carrying the org. number) declares the site and its identity fields carry
      the legal name.

   Parked pages, cross-domain redirects without proof, address-like names, holding-company names, role-holder
   surnames and sites showing another company's number are held back (`ambiguous` / rejected), or labelled as a
   related group site. Every decision is recorded with its reason.
5. **Company-owned facts.** From a verified site only: company-owned social profiles, role mailboxes, a
   self-description and dated news. robots.txt is honoured, with an identifying User-Agent and bounded pages per site.
6. **Hiring.** NAV's public vacancy feed is read once per run; an ad is published only when its employer org. number
   is the company or one of its registered workplaces.
7. **Tail pass.** Requests that a phase left unused are spent on families that failed only because their budget ran
   out (exact-key lookups first, then websites), still inside the global cap.
8. **Refresh.** If the output folder already holds a run, it is archived to `history/` and the new run is diffed
   against it on stable claim keys: typed changes (new filing, new role, address change, new or closed workplace,
   new job…), material or minor. Unreadable sources are carried forward with their original evidence, never reported
   as removed.
9. **Synthesis.** Deterministic templates write the brief in English and Norwegian; every sentence lists the claim
   ids it rests on, and derived values (growth, margins, equity ratio) are labelled as derived. Data checks such as
   the balance-sheet identity and employees vs workplaces are reported as pass/warn and never change values.
10. **Envelopes and report.** Exactly one envelope per input (a watchdog and a fallback envelope guarantee this even
    on crashes), contract validation, a run report (coverage, identity gate per discovery source, requests by host
    and phase, p50/p95, cost), an identity-audit file and the showcase site.

### 4.2 Safety and source rules
- An SSRF-safe, robots-aware fetcher; only permitted sources ([SOURCES.md](SOURCES.md)). No search engines, social
  platforms or directories are scraped.
- Personal data is minimised: role holders' names only, role mailboxes only.
- No caches between runs. `--previous` reads only the agent's own earlier output.
- The local console binds to localhost, checks Host and Origin, and runs only whitelisted commands
  ([SECURITY.md](SECURITY.md)).

### 4.3 User interfaces
- **Showcase** (static, per run, works from a file, also hosted on GitHub Pages for the 1,000-profile run): overview
  with search, a live example fact, portfolio charts, a trust panel and coverage with 95% intervals; a sortable,
  filterable company explorer with CSV export; profiles with a completeness ring, cited summary, account charts,
  filing history, roles, workplaces (optional map), jobs, activity, changes and the identity audit; an evidence
  drawer showing the source text, hash and method for any fact; compare (up to four companies), changes and method
  views. Light glass design, Norwegian/English, mobile layout, keyboard shortcuts.
- **Live console** (local): run the agent, tests, benchmark, evidence re-verification and refresh replay from the
  browser; a live terminal, coverage bars and budget meters; a per-company "why" dialog with identity-gate decisions;
  re-run one company; diff two runs. The showcase home page includes an embedded terminal connected to it.
- Shared design system: [DESIGN.md](DESIGN.md).

### 4.4 Quality process
- **Frozen batches:** `smoke-100` (dev), `val-100`, `batch-1000`, `known-15`; no tuning on official batches.
- **Evaluation tools:** coverage benchmark with Wilson intervals, evidence re-verification (re-fetch sources and find
  the span again), refresh replay (injected changes, idempotency, carry-forward), headless UI checks for both UIs.
- **Tests:** 18 unit tests covering the org-number checksum, identity guards, refresh idempotency, carry-forward,
  the output contract, malformed input, the brief, the tail pass and seen-counters.
- **Clean-machine CI** on every push: `uv sync --frozen`, the tests and a live 5-company run.
- **Hand audits:** every newly accepted website is checked against the live site before it can enter a reported run.
  Full audits with findings and fixes are in [docs/dev/audit_3.md](docs/dev/audit_3.md).
- **Provenance:** reports are regenerated from a fresh clone of the commit they describe; the agent version is stamped
  `-dirty` if a run is made from uncommitted code.

Built with AI coding assistance; the code, rules and audits are in the repository.

---

## 5. Benchmarks

### 5.1 Execution and limits
| Run | Valid envelopes | Requests | Time | External cost |
|---|---|---|---|---|
| 100 random companies (the daily test size) | **100 / 100** | 899 of 2,000 | 4.1 min of 45 | **$0.00** |
| 1,000 random companies | **1,000 / 1,000** | 1,920 of 2,000 | 2.9 min of 45 | **$0.00** |

Published facts: 8,054 for the 100 companies (80.5 per company) and 65,126 for the 1,000 companies. Evidence-incomplete
references: **0** in both.

### 5.2 Coverage, 100 random companies
Share of companies with published facts per family, with the 95% Wilson interval. "Ambiguous" = a candidate was
found but identity could not be proven, so nothing was published.

| Family | Available | 95% CI | Ambiguous (abstained) | Not available |
|---|---|---|---|---|
| Legal identity | 100% | 96–100% | 0% | 0% |
| Registry status | 100% | 96–100% | 0% | 0% |
| Industry | 100% | 96–100% | 0% | 0% |
| Annual accounts | 100% | 96–100% | 0% | 0% |
| Leadership and roles | 100% | 96–100% | 0% | 0% |
| Dated activity | 100% | 96–100% | 0% | 0% |
| Registered workplaces | 78% | 69–85% | 0% | 22% |
| Contact | 31% | 23–41% | 0% | 69% |
| Official website | 17% | 11–26% | 33% | 46% |
| Self-description | 9% | 5–16% | 0% | 91% |
| Company-owned profiles | 8% | 4–15% | 0% | 92% |
| Group structure | 5% | 2–11% | 0% | 0% (95% are not in a group: `not_applicable`) |
| Job postings | 0% | 0–4% | 1% | 99% |

Derived: at least one filed annual-account year for 100%, material dated activity for 100%, real parent/subsidiary
relations for 4%.

Identity gate on these 100 companies: **17 websites published**; 22 candidates held back as ambiguous, 14 rejected
(e.g. the site shows a different company's org. number), 6 blocked by robots.txt, 8 unreachable, 1 labelled as a
related group site.

### 5.3 Coverage, 1,000 random companies
At this size the 2,000-request cap is the binding limit: about one request per company per family. Exact-key
official facts come first.

| Family | Available |
|---|---|
| Legal identity, status, industry, annual accounts, dated activity | 100% |
| Leadership and roles | 37% (up from 32% thanks to the tail pass) |
| Registered workplaces | 28% (up from 22% thanks to the tail pass) |
| Contact | 17% |
| Group structure | 5% |
| Website, profiles, self-description, jobs | about 0% (budget spent on official facts first) |

Filing history is skipped above 200 companies because that endpoint is rate-paced; the latest accounts are still
collected for every company.

### 5.4 Precision, evidence and refresh
| Check | Result |
|---|---|
| Wrong-company publications in hand audits | **0** (every published website checked against the live site) |
| Evidence completeness (URL, retrieval time, SHA-256, span on every fact) | **100%** |
| Evidence re-verification (30 random sources re-fetched, span found again) | **30 / 30** |
| Refresh replay: idempotent re-run | **0 false changes** |
| Refresh replay: injected changes detected and typed | **6 / 6** (new filing, address change, new job, ended role, new role, closed workplace) |
| Refresh replay: unreadable source carried forward | **PASS** |
| Financial values | copied verbatim from Regnskapsregisteret with unit and period; missing values stay missing |

### 5.5 Honest limitations
- **Coverage** is scored against Builderr's pooled reference set, which we cannot see. Websites (17%) and job postings
  (about 0–1%) are the weakest families. That is partly structural (few small companies have a website or open
  vacancies) and partly the price of the strict identity gate.
- At 1,000 companies the request cap leaves most companies without web-based facts.
- No ratings, reviews or sentiment: no permitted keyless source was found, so these are not collected.
- Raw page snapshots are not stored. Evidence keeps the hash and the exact span, but not the full page body.

---

## 6. What's next
- More exact-key official sources (sector registers such as food-safety inspections, construction approvals,
  financial licences) for coverage with zero identity risk.
- More website proof types (org. number in linked terms or privacy pages, JavaScript-rendered sites), each
  hand-audited.
- Careers-page job boards linked from verified sites.
- An evidence snapshot vault with character offsets and offline replay.
- Freshness rules per source, so refreshes spend requests where change is likely.

---

## 7. Where to find things
| What | Where |
|---|---|
| Run it, launch the dashboard, command reference | [README.md](README.md) |
| Requirements checklist and submission details | [SUBMISSION.md](SUBMISSION.md) |
| Committed evidence for every number above | [reports/](reports) (`benchmark.md`, run reports, envelopes, identity audit, refresh replay) |
| Live 1,000-profile showcase | https://harshgitty58.github.io/SignalPost/ |
| Sources and licences / security policy | [SOURCES.md](SOURCES.md) · [SECURITY.md](SECURITY.md) |
| Design system | [DESIGN.md](DESIGN.md) |
| Planning, audits, benchmark policy | [docs/dev/](docs/dev) |
