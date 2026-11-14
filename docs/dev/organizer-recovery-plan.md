# Organizer recovery plan — 14 November 2026

Status: core safeguards implemented; release and ranking gates remain open. See [full diagnosis](../../reports/organizer-diagnosis-20261114.md) and [validation report](../../reports/recovery-validation-20261114.md). The entry-specific resubmission deadline is **15 November, 09:00 IST**. This plan supersedes ranking optimizations until independent accuracy and useful external coverage are measured.

## P0 — Stop wrong-company publication

1. Replace weakened legal-name matching with explicit identity proof. Keep legal-form and ownership context; distinguish a brand alias from a legal name. Verify exact org number or unambiguous full legal identity. Reject conflicting country/entity scope, parent/manager ownership and ambiguous shared domains. Registry URLs and email domains remain candidates.
2. Represent identity decisions structurally: target org, matched legal name, proof URL/span, proof method, scope host/path, relationship and rejection code. Downstream facts must reference that proof and remain within its verified scope.
3. Add tests for OTIS India, Worldwide, the Norwegian legal-name positive control, manager domains, same-domain country redirects, sibling-company links, footer supplier text and multiple organisations. Exercise the full pipeline, not only a name helper.
4. Separate ownership revocation from transient source failure. Revoke dependent website/social/description/contact/news/job claims when identity is contradicted. Preserve a historical correction with evidence; prevent stale/revoked values appearing as current in all index, detail, compare, synthesis and metrics consumers.
5. Reject shared-brand social handles unless the source explicitly attributes the account to the target legal entity. Keep parent relationships labelled and separate. Avoid scraping restricted account destinations.
6. Fix article classification before increasing news discovery: the fresh run published a contact directory and careers landing page as its only two news items. Require actual post content and context before accepting publication metadata. Add Norwegian/English utility-page negatives and genuine dated-article positives.

**Exit gate:** both disclosed organizer examples safe; no foreign-region description or utility-page news; all adversarial ownership/lifecycle/article tests pass; live canary independently reviewed. Do not release an empty external output as a coverage solution.

## P1 — Recover useful external coverage without weakening identity

1. Add stage counters and candidate rejection codes: no candidate, robots blocked, fetch failure, budget unattempted, ambiguous ownership, invalid detail URL, missing publication date, wrong publisher/employer, expired item. Distinguish company news from registry events and site jobs from NAV jobs.
2. Review accepted websites plus a stratified unresolved sample. Independently identify dated news and active vacancies before running extraction, creating positive and negative controls. Freeze labels and inputs; keep development and held-out evaluation separate.
3. Reserve enough requests for at least one full identity attempt per candidate company; release unused phase allocations. Compare legacy and breadth on identical retained responses before live confirmation. Use official bulk records where lawful and compatible with the supplied registry snapshot. Do not sacrifice identity to increase the accepted count.
   Bound bulk-source waiting separately: the diagnostic roles download failed after a long partial transfer. Reserve time for fallback and external enrichment; test unavailable/slow/truncated archives without falsely reporting full enrichment success.
4. Prioritize verified-site RSS, news indexes and article detail pages. Support documented structured-data variants and visible publication dates. Preserve detail URL, date semantics, publisher identity and exact evidence. Never infer publication from lastmod/updated alone.
5. Follow explicit careers links to permitted ATS providers with bounded adapters, exact employer identifiers and individual active ads. Add visible-HTML job extraction where the evidence supports it. Preserve date and closure checks. NAV remains explicitly blocked unless approved deployment access is actually supplied.

**Exit gate:** independently verified live positives for news and jobs, negative controls reject landing/search/parent pages, measurable improvement on a held-out positive pool, no ownership regression, runtime and outbound limits respected.

## P1 — Make the release and public site match the tested code

1. Regenerate the public sample after attribution fixes. Review every published external claim in the sample; remove unsupported legacy values. Update Pages data and a manifest containing commit, code digest, input digest and run timestamp.
2. Verify search, profile, two-company compare, evidence links, stale labels and keyboard/mobile use. Run existing resilience checks in CI and add current-versus-historical publication assertions.
3. Run the complete regression suite, offline artifact audit, refresh replay, a fresh 100-company canary and a large budget-constrained batch on the final source. Record actual commands, source cutoff, errors and provenance. Avoid rerunning expensive batches for documentation-only edits.
4. Freeze the final branch/hash only after checks pass. The user will push. Compose a factual reply naming the exact repository, branch and full hash; include measured results and remaining limits, not a predicted winning score. Confirm the organizer acknowledges this version.

## Measurement gates

| Measure | Gate / reporting rule |
|---|---|
| Wrong-company external claims | Zero known unresolved release blockers; count directly reviewed errors |
| Checked-claim accuracy | Target at least organizer-required 95%; report numerator, denominator and sampling method |
| Precision uncertainty | Stratified external audit, independent labels, interval and unresolved cases; do not dilute with registry facts |
| Recall | Independent company-field opportunity pool; company and item recall separately; no guessed official score |
| News and jobs | Verified dated detail pages and active individual ads, not registry activity or landing pages |
| Refresh | Conflict revokes; temporary failure preserves marked history; closed jobs and unchanged records behave correctly |
| Evidence | Exact claim/entity/date support plus hash/locator integrity; audit financial scope separately |
| Execution | One terminal envelope per input and supplied request/time/cost limits; distinguish completion from successful enrichment |
| Product | Public sample references final audited run; stale/invalid claims do not appear current |

If time is insufficient, prioritize P0, a reviewed canary and an honestly scoped release. Adding more unsupported discoveries will worsen qualification risk. A high score or top-three finish cannot be promised from local tests.
