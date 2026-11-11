"""Re-fetch every published website and recheck exact entity ownership.

This is a deterministic source audit, not independent precision ground truth.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from signalpost.budget import Budget
from signalpost.http import Fetcher
from signalpost.registry import fetch_entities
from signalpost.web import visit_site


def main(source: Path, output: Path):
    entries = []
    for line in source.read_text(encoding="utf-8").splitlines():
        env = json.loads(line)
        site = next((c["value"] for c in env["claims"] if c["field"] == "official_website" and c.get("availability", "available") == "available"), None)
        if site:
            entries.append((env, site))
    budget = Budget(max_requests=300, max_seconds=180, safety_requests=0, safety_seconds=10)
    fetcher = Fetcher(budget, api_concurrency=4)
    try:
        entities, errors = fetch_entities(fetcher, [e["organisation_number"] for e, _ in entries])
        def check(entry):
            env, url = entry
            org = env["organisation_number"]
            if org not in entities:
                return {"organisation_number": org, "decision": "unavailable_registry"}
            entity, _ = entities[org]
            related = {c["value"].get("organisation_number") for c in env["claims"] if c["family"] == "group" and isinstance(c.get("value"), dict)}
            visit = visit_site(fetcher, url, "registry_declared" if entity.get("hjemmeside") else "previous_verified", org, entity, entity["navn"], related)
            proof = visit.proof_page
            return {"organisation_number": org, "legal_name": entity["navn"], "url": url, "decision": visit.decision,
                    "reason": visit.reason, "quote": visit.proof_span,
                    "source_url": proof.url if proof else None, "content_sha256": proof.snap.sha256 if proof else None,
                    "retrieved_at": proof.snap.retrieved_at if proof else None}
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(check, entries))
    finally:
        fetcher.close()
    report = {"checked": len(rows), "accepted": sum(r["decision"] == "accepted" for r in rows),
              "passed": bool(rows) and all(r["decision"] == "accepted" for r in rows), "registry_errors": errors,
              "operations": budget.report(), "rows": rows,
              "limitation": "Revalidation by the publication gate, not an independent population precision estimate."}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"rows", "operations"}}))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
