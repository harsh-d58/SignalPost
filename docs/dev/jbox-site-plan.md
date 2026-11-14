# JBOX Signalpost site — build and submission plan

## 14 November steering

Agent recovery checkpoint is documented in `reports/recovery-validation-20261114.md`. JBOX work can now
proceed as a separate product track. The page structure is fixed below; apply the premium light visual system
after the core flow is built. Inspiration links supplied by the user:

- https://signalpost-research.sites.jboxai.com/
- https://9-copy-ready-jbox-prompt-create-docs-jbo.sites.jboxai.com/
- https://build-signalpost-a-premium-public-read-o.sites.jboxai.com/
- https://nordic-company-lens-live.sites.jboxai.com/
- https://build-signalpost-a-polished-norwegian-co.sites.jboxai.com/
- https://xoejf74ky19lkpr0t0quic93.preview.jboxai.com/?__jbox_source=published&__jbox_revision=c0730bc0ef02de9b

The historical status below predates the active project; see `jbox-build-checkpoint.md` for its provenance.

## Published companion

The user supplied the current public JBOX site: [Signalpost read-only company research](https://build-signalpost-a-read-only-norwegian-c.sites.jboxai.com/). The repository README links to it. Before describing detailed functionality or claiming the JBOX bonus submission is complete, verify the live search, two-company comparison, evidence links, responsive layout and data-export revision in the published site. The browser inspection tool was unavailable during the repository-link update.

Prepared 13 November 2026 (Asia/Calcutta); updated 14 November. A public companion link is now supplied by the user and recorded above. Its detailed behavior, export revision and JBOX build provenance have not been verified in this repository session.

## Eligibility and access

The [bonus section](https://builderr.ai/challenges/signalpost#scoring) still specifies 7 November, 23:59 IST for site links, while the voting banner closes 16 November. An extension for new bonus entries is unconfirmed. Ask the organizer whether a new JBOX project is still eligible and whether gallery qualification applies. Do not describe voting's end date as the entry deadline.

[JBOX](https://jboxai.com/) advertises prompt-to-product flows, Next.js, code export, GitHub and hosting. It offers 50 starting credits; additional credits are advertised at $20 per 100. Verify actual workspace capabilities and remaining credits before building. Do not purchase credits automatically.

Actual JBOX use is necessary: a locally built site cannot simply be relabeled as JBOX-built. Retain the project URL, build history and exported revision as provenance. A user-controlled logged-in JBOX session is needed at implementation time; no password or token should be placed in chat or repository files.

## Product objective

A visitor should find a Norwegian company, compare it with another, and trace a fact to its source without learning the crawler's implementation. The initial release is a read-only company research product using existing supported outputs, not a new crawler or fabricated demonstration dataset.

## Architecture and existing work

- Preserve the Python agent and existing GitHub Pages showcase while building the JBOX version separately.
- Reuse the information model and tested interactions from `src/signalpost/showcase/template.html`: search, profiles, comparisons, citations and dates.
- Export a sanitized public dataset from real envelopes: compact search index plus per-company JSON loaded on demand. Begin with a documented 100-company sample; expand only after validation.
- Use stable organisation numbers as IDs. Retain claim/evidence references, periods, units, account scope, availability and observation dates.
- Exclude secrets, debug traces, local paths and unapproved raw snapshots. Publish permitted source links and excerpts only. Mark historical data with its observation time.
- Prefer a static/read-only data adapter for tonight's scope. Add server-side storage only if required by the JBOX workflow. Do not add login, billing, user accounts or live crawl controls to the public demo.
- Inspect JBOX's import/export capabilities first. If existing code cannot be imported, generate the new UI inside JBOX from a complete brief and connect the exported data contract. Preserve evidence of that build process.

## Screens and acceptance criteria

### 1. Find — company search and discovery

A search-first entry page with a concise explanation, name/org-number search, usable sample companies and dataset observation date. Results show legal name, organisation number, municipality and an explicit data-availability summary. Search supports Norwegian characters and spacing in organisation numbers.

Acceptance: exact org-number lookup works; name search yields relevant matches; empty/error states explain next steps; keyboard and touch users can open a result. Do not imply the sample covers every Norwegian company.

### 2. Company — profile and facts

Show legal identity prominently, then business description, financial facts, people/locations and eligible external activity. Each fact has a source action. Clearly label group versus company scope and reporting periods. Unsupported fields stay missing/ambiguous/blocked; missing financial values never become zero.

Acceptance: a visitor can distinguish entity identity, reporting period and source freshness without opening implementation details. No synthetic accuracy badge or unsupported growth/hiring statement.

### 3. Compare — two-company view

Offer an obvious add-to-compare action and persistent selection tray. Compare exactly two for the initial release, with replace/remove actions. Align rows by field, currency, period and account scope. Mark mismatches rather than computing misleading differences.

Desktop: side-by-side columns. Phone: aligned compact columns where readable, otherwise paired values per field; no whole-page horizontal overflow. Keep source actions available for both values.

Acceptance: selecting two, replacing one and opening either value's evidence all work. A shared comparison link restores both selections.

### 4. Evidence — source and date detail

Desktop side panel; mobile full-height sheet/page with accessible close/back behavior. Show the fact, source URL, permitted supporting excerpt, retrieval date and effective/publication/reporting date separately. Include scope, stale status and claim ID where useful. Open external links safely.

Acceptance: evidence is reachable within two interactions of the fact. Keyboard focus enters the view and returns to its trigger. A direct claim link opens the correct company and evidence. Missing or inaccessible sources have a clear fallback.

### 5. Method — sample, sources and limitations

Explain sample size, observation dates, permitted sources, missing states and how refresh works. Link the repository and methodology. Name JBOX only after an actual project exists. Do not display an aspirational competition score as a result.

## Visual direction

A restrained research interface: readable typography, strong legal-identity hierarchy, neutral surfaces and one accent color for actions. Use space and alignment to make values and sources easy to scan. No decorative dashboards, arbitrary confidence percentages, fabricated logos, autoplay or animation that slows research.

Optimize first for 390px phone and 1366px laptop widths, then check 360px and tablet layouts. Use 44px touch targets where practical, visible focus, semantic headings and good text contrast. Keep search, comparison and source actions visually consistent.

## Build sequence and estimated effort

These are estimates after access is available; JBOX build time and credits may change them.

1. Access/capability check (15–30 minutes): inspect workspace, available credits, project creation, export and hosting. Confirm entry eligibility separately; reusable preparation can continue meanwhile.
2. Data contract and public sample (30–60 minutes): choose a real dated sample, validate evidence references and produce minimal index/profile exports. Record input hashes and excluded fields.
3. JBOX product generation (60–120 minutes): submit one complete brief covering routes, data contract, layouts, edge cases and acceptance criteria. Review the generated flow before consuming build credits. Implement search/profile/evidence first, then comparison.
4. Data integration and polish (45–90 minutes): connect real exports, remove invented demo facts, verify dates, scope and availability, and fix phone interactions.
5. QA and deployment (45–60 minutes): run the task checks below, publish only the reviewed public bundle, test the live URL and retain the exported revision/build provenance.
6. Submission draft (15 minutes): prepare the email after the site is live and verified. Include site link, JBOX provenance, repository/commit and honest sample limitations. If eligibility is unresolved, explicitly request acceptance rather than claiming eligibility.

Likely total: approximately 3.5–6 hours after access, not a promise of completion tonight. If time is tight, omit extra charts, theme switching and animation; preserve all three core user tasks.

## QA checklist

- [ ] Name and exact-number search, Norwegian text, no results and invalid query.
- [ ] Profile with rich data, sparse data, group accounts and blocked sources.
- [ ] Two-company comparison; different periods/units; replace and remove selection.
- [ ] Every sampled displayed fact maps to an actual source-backed claim.
- [ ] Source drawer, direct claim link, external source, Escape/back and focus return.
- [ ] Mobile touch and keyboard navigation; no clipped values or page overflow.
- [ ] Refresh/reload/deep links on deployed host; no broken asset paths.
- [ ] Slow network, missing profile file and failed source link.
- [ ] No browser-console errors, leaked secrets, local paths or unapproved evidence content.
- [ ] Real-browser checks at laptop/phone sizes and automated interaction checks where supported.
- [ ] Public link works without builder login; JBOX project/export provenance retained.

## Tonight's email package

Do not send a completion email while the project is only a mockup. Deliver: live site URL, JBOX project/build proof, exact code revision where available, dated sample description, tested find/compare/source flows, known limitations and deadline clarification if still unresolved. The user sends the email; no automatic sending is part of this plan.

## Separate urgent agent follow-up

The updated board now has a row explicitly named Harsh Dhavane with 24.58/100. Confirm the evaluated commit and request the evaluator's claim-level failure report before mapping that score to the current working tree. A new site cannot repair incorrect agent facts. Preserve agent-accuracy work as a separate priority while building this UX entry.
