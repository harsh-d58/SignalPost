# Sources, rights and access policy

The recovery revision also uses the [Greenhouse Job Board public GET API](https://docs.greenhouse.io/job-board.html).
Only a board linked from an exact-company page is queried (at most one board and two individual ads per company).
Publication requires the detail response's `company_name` to equal the full legal name, `first_published` to be valid,
and any application deadline to remain open. `updated_at` is never used as a publication date. Prospect posts are excluded.
No application is submitted, no credentials are needed, and API responses are retained as evidence excerpts.
Other ATS providers remain unsupported; their presence does not authorize scraping.

| Source | Endpoint(s) | Licence / terms | Access pattern |
|---|---|---|---|
| Enhetsregisteret | `data.brreg.no/enhetsregisteret/api/enheter?organisasjonsnummer=…` (≤100 per call), `/enheter/{org}/roller`, `/underenheter?overordnetEnhet={org}`, `/konsernstruktur/{org}`, `/oppdateringer/enheter`, `/oppdateringer/roller` | NLOD 2.0 open data | documented open API, ≤8 concurrent |
| Regnskapsregisteret | `data.brreg.no/regnskapsregisteret/regnskap/{org}` | NLOD 2.0 | 1 call per company |
| NAV vacancy feed | `pam-stilling-feed.nav.no/api/v1/feed`, `/feedentry/{uuid}` | [NAV access and terms](https://navikt.github.io/pam-stilling-feed/) | requires `NAV_FEED_TOKEN` approved for the deployment; otherwise blocked without a request. `--allow-public-nav-token` is an explicit private-development experiment, not official-run permission. Detail ads require exact employer/subunit and current ACTIVE status. |
| Wikidata | `query.wikidata.org/sparql`: one query per 100 org. numbers for items whose Norwegian org. number (P2333) is in the batch, returning their official website (P856) | CC0 | website *candidate* only; the site must still pass the identity gate |
| Company websites | registry-declared site (company or registered workplace), registry e-mail domain, Wikidata P856, `<name>.no` | company-owned content | robots.txt honoured (incl. 401/403 = disallow), identifying User-Agent, ≤2 concurrent per host. Each candidate can use a homepage and up to 3 identity subpages; an accepted site can add up to 2 careers pages, 1 feed and 3 news pages. All requests, redirects and robots checks consume the shared budget. Default response cap is 3 MB. |

**Not used:** search engines, LinkedIn/Meta/Glassdoor/Indeed or any unofficial client, directories
(proff.no, gulesider, purehelp, 1881…), `w2.brreg.no/kunngjoring` (disallowed by its robots.txt).
Social profile URLs are only *links found on the verified official site*; the platforms are never fetched.

**Personal data:** role holders' names only (birth dates dropped, deceased persons skipped); e-mail
limited to role mailboxes (post@, info@…) on the company's own domain; registry phone not shown for
sole proprietorships.

**Showcase (viewer side, optional):** the workplace map sends registered addresses to Kartverket's address API
(`ws.geonorge.no/adresser/v1/sok`, CC BY 4.0) only when the reader presses “Show on map”. It is not part of any run.

## Retention and reproducibility

| Source | Retained artifact | Source rights and failure behavior |
|---|---|---|
| Registry and accounts | Private content-addressed JSON with birth dates, personal identifiers and contact fields removed; original-response and retained-object digests are separate | NLOD 2.0. Published business contacts retain a separate excerpt. No authorized/person-number endpoints are used. Source failure preserves supported prior values as stale. |
| Roles/workplaces bulk | Only selected entity records, archive SHA-256, original bulk URL, retrieval time, row selection and transformation | NLOD 2.0. Whole downloads are temporary and deleted. An incomplete inventory never establishes absence. Direct lookups remain the fallback. |
| Company-owned pages | Published excerpts, URL, redirects, observation time, original digest and extraction method; no raw HTML archive | Respect robots and the source's access terms. Robots alone is not a licence. Do not enable a route where the method or retention is prohibited. A retained excerpt proves the extraction artifact's integrity, not independent full-page support. |
| NAV | Published ad excerpts only; no raw feed, ad HTML, contacts, tokens or Authorization headers | A credential must cover the submitted use and public showcase. Unreadable ads are not carried into the current public profile. Exclude NAV until deployment permission and withdrawal handling are approved. |
| Wikidata | Candidate URLs only | CC0. A candidate cannot support a company claim without reverse verification. |

Artifacts under `<out>/snapshots/` are private run evidence, not copied to the generated showcase. Every published evidence record refers to a snapshot and a quote or JSON-pointer locator. Financial locators include the record index, currency and reporting period. `eval/snapshot_audit.py` verifies file digests and locators offline and reports excerpt-only artifacts separately. Original full-response digests cannot be recomputed from privacy-minimized JSON and are explicitly labeled as such.

**Caches and evaluator identity:** live HTTP responses are not reused across runs. `--bulk` is an explicitly declared local discovery cache. `--registry-snapshot` is the authoritative evaluator identity input and requires its observation timestamp through `--registry-snapshot-at`. Its file digest and identity policy appear in the run report. Missing frozen records remain unavailable for research, rather than falling through to live identity. `--previous` reads this agent's prior output and copies referenced retained evidence into the new run. The original output directory remains private historical evidence. No snapshots, tokens or source bodies enter Git by default.

**Cutoff:** `--evidence-cutoff` excludes observations and claim-effective/reporting dates after the supplied timestamp. It cannot reconstruct a past website from a current fetch. An older evaluator cutoff therefore yields explicit gaps for current live observations. Retention-safe historical evidence must be supplied with its original observation time, not relabeled as a current discovery.

**Official declarations:** no LLM, paid search, unofficial platform clients, independent review or sentiment source. External API cost is $0 for the default connector set, excluding compute, bandwidth and development tooling. NAV is blocked by default without an approved credential. Search-like and registry website candidates are never independent evidence of website ownership.

**Credential configuration:** [.env.example](.env.example) documents the optional `NAV_FEED_TOKEN` variable. The
agent reads process environment variables; loading `.env` requires an explicit `uv run --env-file .env`.
Restart a running local backend after changing its environment. Do not commit real credentials or source snapshots.
