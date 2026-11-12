# Email draft — submission to Builderr

**To:** submit@builderr.ai
**Subject:** Signalpost revision — Signalpost Agent — <short sha>
**Attachment:** `signalpost-code.zip` (the code at the submitted commit: `git archive --format=zip -o signalpost-code.zip HEAD`)

Before sending, replace `<40-char sha>` / `<short sha>` with the output of `git rev-parse HEAD` (after
`git push origin main`) and `<your name>` with your name.

---

Hello Builderr team,

Please find my revised entry for the Signalpost challenge. This revision checks website ownership, social handle identity, article publication dates, and the employer of each individual vacancy before publishing those facts.

**Agent:** Signalpost Agent
**Builder and contact:** <your name>, harshvdn.2@gmail.com
**Repository:** https://github.com/harshgitty58/SignalPost
**Exact commit:** <40-char sha> — https://github.com/harshgitty58/SignalPost/commit/<40-char sha>
**Code:** attached as `signalpost-code.zip` (identical to that commit)

**One command to run it**
```
uv run --frozen signalpost run --organisations official-batch.jsonl --registry-snapshot official-registry.jsonl --registry-snapshot-at 2026-11-09T00:00:00Z --evidence-cutoff 2026-11-10T00:00:00Z --bulk-files --workers 8 --job-days 7 --max-requests 2000 --max-minutes 45 --max-cost 10 --out out-official
```
Replace the example paths, timestamps and limits with the supplied evaluation values. The run writes one terminal
envelope per input to `out-official/envelopes.jsonl`, a run report and a static showcase. Reusing the output directory
archives the previous run and reports changes.

The 100-company smoke report is `reports/release-validation100-metrics.json`. The same-batch comparison and verification results for 1,100 companies are in `reports/release-readiness-20261112.md`. GitHub Pages builds the committed 1,000-profile sample. [Showcase](https://harshgitty58.github.io/SignalPost/) · [Sample profile](https://harshgitty58.github.io/SignalPost/#/c/999072712)

**Model / API details**
- No LLM is used.
- Brønnøysundregistrene open APIs: Enhetsregisteret, Regnskapsregisteret, roles, sub-units, group structure, change log (NLOD 2.0).
- NAV pam-stilling-feed requires an approved `NAV_FEED_TOKEN`. Without it, NAV is blocked and company-owned careers discovery continues.
- Wikidata SPARQL (CC0), used only to find website candidates; every site must pass an exact-entity identity gate.
- Company-owned websites, robots.txt honoured, published only after the identity gate.
- No paid APIs.

**Expected run cost:** $0.00 in third-party / external API costs per run (limits enforced by default: 45 minutes,
2,000 outbound requests, $10).

Every published fact carries its source URL, retrieval time, reporting period (where relevant), content SHA-256,
claim span and extraction method. Anything that cannot be tied to the exact legal entity is returned as `ambiguous`
or `not_available` instead of being published. Source rights are in `SOURCES.md`, the outbound URL policy in
`SECURITY.md`, and a requirement-by-requirement checklist in `SUBMISSION.md`.

Thank you,
<your name>
