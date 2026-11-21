# How Builderr tests Signalpost submissions

This describes the published procedure in the 19 November 2026 scoring PDF, evaluation contract v2, participant brief, and organizer feedback. See [Signalpost rules](SIGNALPOST-RULES.md) for deadlines and source precedence.

## Official evaluation

1. **Freeze the entry.** Builderr evaluates the submitted exact commit. Supply a 100-company smoke report, pinned setup, one evaluator command, model/API/licence declarations, cost, and contact details. The playbook describes the clean-machine check as a fresh checkout and empty virtual environment using only the declared setup and run steps. Frozen revisions apply to later batches.
2. **Supply a common batch.** Builderr selects the organisation numbers after the cutoff and supplies the frozen registry snapshot, output contract, cutoff, network policy, and fixed resource budget. Eligible entries receive the same inputs and limits, including unfamiliar companies. The public universe and locally selected smoke and scale batches are for development. The shared evaluation can grow from 1,000 to 1,100 companies, and Builderr plans a larger test for leading agents before choosing winners.
3. **Validate execution and result envelopes.** Each company must produce one terminal envelope, with identity, claims, evidence, availability, snapshot references, refresh metadata, and errors as applicable. Check budget compliance, explicit missing or blocked states, absence of fabricated values, documented source rights, safe outbound URLs, and server-side credentials. A timeout or missing envelope prevents scoring that run.
4. **Check published claims.** Verify exact legal entity, factual correctness, source support, retrieval date, and any applicable publication/effective date or reporting period. In the disclosed audit of commit `eaef804`, Builderr checked 22 claims. Fourteen were correct and eight concerned the wrong company. The two disclosed examples were a housing manager's domain assigned to a cooperative and the global Otis YouTube account assigned to OTIS AS. [Organizer audit record](reports/organizer-diagnosis-20261114.md)
5. **Require reproducible refresh.** The same source snapshot must yield no duplicate records or false changes. A refresh must preserve earlier evidence and expose material changes. These are published checks. Builderr's private refresh fixtures and test sequence were not supplied.
6. **Grade synthesis and UX.** A useful synthesis explains what the company does, what changed, and what remains unknown, with evidence. UX grading covers finding a company, comparing two, and verifying facts on desktop and phone.

## Score and qualification

| Component | Points |
|---|---:|
| Recall and coverage | 50 |
| Precision, identity, and evidence | 30 |
| Synthesis | 12 |
| UX | 8 |

- Builderr verifies and deduplicates pooled discoveries from submitted agents and its own crawlers. The collection is versioned and everyone is rescored against the same pool. It freezes after eligible final submissions are checked.
- For each external information type, the published formula is **70% company recall + 30% individual-fact recall** against that collection. Finding 30 of 50 jobs across 15 of 20 companies yields 70.5% for jobs. The detailed contract marks recall unmeasured when the pool lacks at least 15 positive company–field opportunities across at least three external families.
- Qualification requires an official run, **65/100 overall**, and **at least 95%** of checked published claims correct and attributed to the right company. A material wrong-company publication or fabricated financial value blocks an official result. Coverage and recall have no separate qualification minimum.
- The directional 500-company board used recall scaling so the top tenth of entries earned about 80% of recall points. That batch excluded reviews, ratings, and sentiment because evidence was unavailable. Those are round-specific notes.
- Final ranking averages scheduled batches while the frozen entry is active. A builder-caused failure or missed batch scores zero after clean reproduction. Builderr harness, infrastructure, or shared-source failures are void and rerun with the same code. Ties favor fewer wrong-company publications, then higher weighted company recall, then lower declared third-party API cost.

## Local equivalents

| Check | Repository counterpart |
|---|---|
| Clean setup, one command, and terminal envelopes | [Clean-machine CI](.github/workflows/ci.yml) and [README run commands](README.md). Use the 100-company smoke test and check larger batch performance separately. |
| Evidence integrity and exact attribution | [Snapshot audit](eval/snapshot_audit.py) checks digests and locators. [Claim adjudication](eval/adjudication.py) records independent review of entity, fact, and date. |
| Coverage and recall | [Metrics tooling](eval/metrics.py). Recall requires a labelled company/fact opportunity pool. |
| Same-snapshot replay and material changes | [Refresh replay](eval/refresh_replay.py) and regression tests. Cover unchanged, changed, blocked, revoked ownership, and closed-job cases. |
| Search, compare, and source evidence | [Frontend regression checks](eval/ui_resilience_check.cjs) plus desktop and phone browser checks. |

Builderr's hidden batches, checked-claim sampling rules, private labels, and detailed point allocation within categories were not supplied. Report the code version, cohort, cutoff, and validation method for local results. The evaluation contract's `npm run check:signalpost*` commands are Builderr's checks, while the links above identify this repository's checks.

Source snapshot reviewed on 19 November 2026, pages 2–8 of the supplied PDF. [Builderr scoring page](https://builderr.ai/challenges/signalpost#scoring)
