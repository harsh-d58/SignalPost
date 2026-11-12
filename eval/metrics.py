"""Measured metrics and explicitly hypothetical score scenarios.

uv run python eval/metrics.py out-run --output reports/metrics.json
Optional --pool independent.jsonl: independently verified claim objects with
organisation_number, family, field, value, and period/unit where applicable.
For accounts, supply account_type (SELSKAP or KONSERN). No predictions are labels.
Optional --baseline out-baseline compares the same organisation set only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from signalpost.web import item_url


def claims(env):
    return [c for c in env["claims"] if c.get("availability", "available") == "available" and not c.get("stale_since")]


def signature(org, claim):
    return json.dumps([org, claim["family"], claim.get("key") or claim["field"], claim["value"],
                       claim.get("unit"), claim.get("period")], sort_keys=True, ensure_ascii=False)


def account_type(claim):
    explicit = claim.get("account_type")
    if explicit:
        return explicit.strip().upper()
    note = re.search(r"\baccount_type=(\w+)", claim.get("note") or "")
    if note:
        return note[1].upper()
    # Older audit and accounting-rules claims carry their account type in the key.
    legacy = re.fullmatch(r"(?:audit|rules):(SELSKAP|KONSERN):\d{4}-\d{2}-\d{2}", claim.get("key") or "")
    return legacy[1] if legacy else None


def reference_signature(org, claim):
    """Match independently labeled facts by their meaning within an exact entity."""
    family, field, value = claim["family"], claim["field"], claim["value"]
    effective_date = claim.get("effective_date")
    if field == "official_website":
        value = item_url(value, "") or value
    elif field in ("company_news", "job_posting") and isinstance(value, dict):
        url = item_url(value.get("url"), "")
        if field == "company_news":
            published = value.get("date") or effective_date
            if url and published:
                value = {"url": url, "date": published}
                effective_date = None
        elif url and isinstance(value.get("employer"), str) and value["employer"].strip():
            employer = " ".join(value["employer"].split()).casefold()
            value = {"url": url, "employer": employer}
            effective_date = None
    scope = account_type(claim) if family == "financials" else None
    return json.dumps([org, family, field, value, claim.get("unit"), claim.get("period"), effective_date, scope],
                      sort_keys=True, ensure_ascii=False)


def measure(run: Path, pool: Path | None = None) -> dict:
    envs = [json.loads(line) for line in (run / "envelopes.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    report = json.loads((run / "run-report.json").read_text(encoding="utf-8"))
    n = len(envs)
    families = sorted({f for e in envs for f in e["availability"]})
    rows = {}
    for family in families:
        published = [(e, [c for c in claims(e) if c["family"] == family]) for e in envs]
        company_count = sum(bool(cs) for _, cs in published)
        rows[family] = {"companies_with_current_claims": company_count, "company_coverage": company_count / n if n else None,
                        "distinct_claims": len({signature(e["organisation_number"], c) for e, cs in published for c in cs}),
                        "availability": dict(Counter(e["availability"][family]["state"] for e in envs))}
    source_counts = Counter(s.get("retention", "unknown") for e in envs for s in e.get("source_snapshots", []))
    ops = report["operations"]
    result = {"run_id": report["run_id"], "code_version": report["agent_version"], "companies": n,
              "measurement_mode": report.get("mode"), "replay_provenance": report.get("replay"),
              "terminal_completion": len({e["organisation_number"] for e in envs}) / report["input_count"] if report["input_count"] else 1,
              "validation": report["validation"], "families": rows,
              "requests": ops["requests"], "requests_per_company": ops["requests"] / n if n else None,
              "elapsed_seconds": ops["elapsed_seconds"], "p50_company_ms": ops.get("p50_company_ms"), "p95_company_ms": ops.get("p95_company_ms"),
              "external_cost_usd": report["third_party_cost_usd"], "external_cost_per_company_usd": report["third_party_cost_usd"] / n if n else None,
              "snapshot_retention_counts": dict(source_counts), "models": report.get("models", []),
              "code_sha256": report.get("code_sha256"),
              "published_current_claims": sum(len(claims(e)) for e in envs),
              "specific_fields": {field: {"companies": sum(any(c["field"] == field for c in claims(e)) for e in envs),
                                           "claims": sum(c["field"] == field for e in envs for c in claims(e))}
                                  for field in ("company_news", "registry_event", "job_posting", "filed_annual_accounts")},
              "precision": None, "wrong_company_publications": None, "official_score": None,
              "reason_unmeasured": "No independent per-claim attribution audit or Builderr reference collection supplied. Coverage and artifact integrity do not establish precision or recall."}
    if pool:
        targets = {e["organisation_number"] for e in envs}
        labels = [c for line in pool.read_text(encoding="utf-8").splitlines() if line.strip() for c in [json.loads(line)] if c["organisation_number"] in targets]
        opportunities = {(c["organisation_number"], c["family"]) for c in labels}
        positive_families = {c["family"] for c in labels}
        sparse = len(opportunities) < 15 or len(positive_families) < 3
        recalled = {}
        actual = {reference_signature(e["organisation_number"], c) for e in envs for c in claims(e)}
        for fam in sorted(positive_families):
            reference = {reference_signature(c["organisation_number"], c) for c in labels if c["family"] == fam}
            matched = reference & actual
            ref_orgs = {json.loads(s)[0] for s in reference}
            found_orgs = {json.loads(s)[0] for s in matched}
            company_recall, claim_recall = len(found_orgs) / len(ref_orgs), len(matched) / len(reference)
            recalled[fam] = {"reference_companies": len(ref_orgs), "reference_claims": len(reference),
                             "matched_claims": len(matched), "company_recall": company_recall, "claim_recall": claim_recall,
                             "weighted_recall": None if sparse else .7 * company_recall + .3 * claim_recall}
        result["local_pool"] = {"sha256": hashlib.sha256(pool.read_bytes()).hexdigest(), "matching": "semantic_v1", "sparse_not_measured": sparse,
                                "company_field_opportunities": len(opportunities), "families": recalled,
                                "scope": "Only this independently labeled local pool; no official score inferred."}
    result["score_scenarios_not_predictions"] = [
        {"name": "qualification_sensitivity", "recall": 24, "evidence": 28, "synthesis": 8, "ux": 5, "total": 65},
        {"name": "posted_leader_sensitivity", "recall": 28, "evidence": 29, "synthesis": 9, "ux": 5, "total": 71},
        {"name": "planning_target", "recall": 32, "evidence": 29, "synthesis": 10, "ux": 6, "total": 77}]
    return result


def compare(base: Path, challenger: Path) -> dict:
    def orgs(path):
        return {json.loads(line)["organisation_number"] for line in (path / "envelopes.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    if orgs(base) != orgs(challenger):
        raise ValueError("A/B comparison requires identical organisation sets")
    before, after = measure(base), measure(challenger)
    return {"baseline": before["run_id"], "challenger": after["run_id"], "companies": after["companies"],
            "coverage_delta_pp": {f: round(100 * (after["families"][f]["company_coverage"] - before["families"][f]["company_coverage"]), 2) for f in before["families"]},
            "request_delta": after["requests"] - before["requests"], "seconds_delta": round(after["elapsed_seconds"] - before["elapsed_seconds"], 2),
            "caveat": "Live source observations can differ in time. Promotion also requires attribution and direct/bulk parity audits."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--pool", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = measure(args.run, args.pool)
    if args.baseline:
        result["comparison"] = compare(args.baseline, args.run)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
