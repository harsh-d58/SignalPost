# Email draft — revised Signalpost entry

**To:** submit@builderr.ai

**Subject:** Signalpost revision — Signalpost Agent — <short commit hash>

Before sending: replace the commit placeholders, confirm the final committed-code smoke report, and attach `signalpost-code.zip` generated from that exact commit. This is a draft; no email has been sent.

---

Hello Soham and Builderr team,

Thank you for the audit feedback. We have worked on the website ownership, social-handle attribution, dated-news and individual-employer checks you highlighted. The agent withholds unsupported matches and preserves explicit blocked, ambiguous and incomplete states.

This update also fixes interrupted website identity checks and adds clearer execution diagnostics in the reports and frontend. The existing scheduler remains the default; a separate breadth-first scheduling experiment is included but is not enabled by the command below.

Agent: Signalpost Agent

Contact: Harsh Dhavane, harshdhavane06@gmail.com

Repository: https://github.com/harshgitty58/SignalPost

Exact commit: <40-character commit hash>

Commit link: https://github.com/harshgitty58/SignalPost/commit/<40-character commit hash>

Install: `uv sync --frozen`

Run:
```bash
uv run --frozen signalpost run --organisations official-batch.jsonl --registry-snapshot official-registry.jsonl --registry-snapshot-at 2026-11-09T00:00:00Z --evidence-cutoff 2026-11-10T00:00:00Z --bulk-files --website-strategy legacy --workers 8 --job-days 7 --max-requests 2000 --max-minutes 45 --max-cost 10 --out out-official
```
Please substitute your supplied input paths, observation timestamps, cutoff and limits. The run produces one terminal envelope per input, retained evidence references, a run report and a static showcase.

Local verification: 282 Python tests and 16 frontend tests passed, alongside source audits, refresh replay and frontend interaction checks. The experiment results and their limitations are documented in `reports/scheduling-improvement-20261113.md`. Independent precision and recall are not claimed.

Final committed-code 100-company smoke report: <path to the verified report for this exact revision>

Models/APIs: no LLM; Brønnøysundregistrene APIs and declared bulk records, Wikidata for website candidates only, and permitted company-owned pages with robots checks. NAV requires an approved `NAV_FEED_TOKEN`; without it the feed is reported as blocked. Source details are in `SOURCES.md`.

Expected external API cost: $0 per run with the current connector configuration, excluding compute and bandwidth. No paid APIs are required.

The code archive attached is generated from the exact commit above. Please record this as our updated version.

Thank you,

Harsh Dhavane
