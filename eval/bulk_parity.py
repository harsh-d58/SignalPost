"""Compare saved bulk findings with direct official lookups on a stratified audit.

uv run python eval/bulk_parity.py out-bulk --sample 30 --output reports/parity.json
Current direct responses can differ from the nightly inventory. Differences fail
promotion pending inspection, rather than being explained away automatically.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from signalpost.budget import Budget
from signalpost.http import Fetcher
from signalpost.model import ProfileBuilder
from signalpost.registry import ROLES_URL, SUBUNITS_URL, roles_claims, subunit_claims


def values(claims, family):
    return {json.dumps([c.get("key"), c["value"], c.get("unit"), c.get("period")], ensure_ascii=False, sort_keys=True)
            for c in claims if c["family"] == family and c.get("availability", "available") == "available" and not c.get("stale_since")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--sample", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.run / "envelopes.jsonl").read_text(encoding="utf-8").splitlines()]
    random.Random(20261109).shuffle(rows)
    present = [e for e in rows if e["availability"]["locations"]["state"] == "available"]
    absent = [e for e in rows if e["availability"]["locations"]["state"] == "not_available"]
    selected = absent[:args.sample // 2] + present[:args.sample - min(len(absent), args.sample // 2)]
    selected_ids = {e["organisation_number"] for e in selected}
    selected += [e for e in rows if e["organisation_number"] not in selected_ids][:max(0, args.sample - len(selected))]
    budget = Budget(max_requests=args.sample * 4 + 20, safety_requests=0, max_seconds=300, safety_seconds=10)
    fetcher = Fetcher(budget)
    audit = []
    try:
        for env in selected:
            org = env["organisation_number"]
            for family, template, handler in [("leadership", ROLES_URL, roles_claims), ("locations", SUBUNITS_URL, subunit_claims)]:
                snap = fetcher.get_json(template.format(org=org), phase="audit")
                row = {"organisation_number": org, "family": family, "source_url": snap.url, "retrieved_at": snap.retrieved_at, "content_sha256": snap.sha256}
                if not snap.ok:
                    row.update(result="unavailable", status=snap.status)
                else:
                    pb = ProfileBuilder(org)
                    handler(pb, snap)
                    expected = values([c.to_dict() for c in pb.claims.values()], family)
                    actual = values(env["claims"], family)
                    row.update(result="match" if actual == expected else "mismatch", bulk_claims=len(actual), direct_claims=len(expected),
                               bulk_only=[json.loads(s) for s in sorted(actual - expected)], direct_only=[json.loads(s) for s in sorted(expected - actual)])
                audit.append(row)
    finally:
        fetcher.close()
    report = {"sampled_companies": len(selected), "checks": len(audit), "matches": sum(r["result"] == "match" for r in audit),
              "passed": bool(audit) and all(r["result"] == "match" for r in audit), "operations": budget.report(), "rows": audit}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
