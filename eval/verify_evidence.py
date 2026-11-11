"""Re-fetch a random sample of evidence sources and check the claim span still appears (evidence validity).

    uv run python eval/verify_evidence.py out-dev/envelopes.jsonl --sample 50
Spans from JSON APIs are compared whitespace-insensitively; drift since the run (e.g. a changed CEO) is
reported as drift, not hidden.
"""
from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from signalpost.budget import Budget  # noqa: E402
from signalpost.http import Fetcher  # noqa: E402


def compact(text: str) -> str:
    return re.sub(r"\s+", "", html.unescape(text))


def span_present(body: str, span: str) -> bool:
    """Require the claimed excerpt, not unrelated occurrences of value words."""
    if not isinstance(span, str) or not span.strip():
        return False
    probe = compact(span)
    if probe in compact(body):
        return True
    try:
        # JSON object formatting and escaping may differ, but field/value structure must agree.
        parsed = json.loads(body)
        normalized = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
        if probe in compact(normalized):
            return True
        try:
            fragment = json.loads(span)
        except ValueError:
            fragment = json.loads("{" + span + "}")
        def contains(actual, expected):
            if isinstance(expected, dict):
                return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k, v in expected.items())
            return actual == expected and type(actual) is type(expected)
        def walk(value):
            if contains(value, fragment):
                return True
            children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
            return any(walk(child) for child in children)
        if isinstance(fragment, dict) and fragment and walk(parsed):
            return True
    except (ValueError, TypeError):
        pass
    try:
        from lxml import html as lhtml
        doc = lhtml.fromstring(body)
        return probe in compact(doc.text_content())
    except (ValueError, TypeError):
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("envelopes")
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    pool = []
    for line in open(args.envelopes, encoding="utf-8"):
        e = json.loads(line)
        ev = {x["id"]: x for x in e["evidence"]}
        snapshots = {x["id"]: x for x in e.get("source_snapshots", [])}
        for c in e["claims"]:
            if c.get("availability", "available") == "available" and c["evidence_ids"]:
                x = ev.get(c["evidence_ids"][0])
                if x and "replay.invalid" not in x["source_url"]:
                    x = dict(x)
                    provenance = snapshots.get(x.get("snapshot_id"), {}).get("provenance", {})
                    if str(provenance.get("kind", "")).startswith("bulk_selected"):
                        from signalpost.registry import ROLES_URL, SUBUNITS_URL
                        template = ROLES_URL if c["family"] == "leadership" else SUBUNITS_URL if c["family"] == "locations" else None
                        if not template:
                            continue
                        x["verification_url"] = template.format(org=e["organisation_number"])
                    pool.append((e["organisation_number"], c, x))
    sample = random.Random(args.seed).sample(pool, min(args.sample, len(pool)))
    fetcher = Fetcher(Budget(max_requests=args.sample * 4 + 50))
    found = drift = errors = 0
    rows = []
    for org, claim, ev in sample:
        api = ev["source_class"] in ("official_registry", "public_api")
        url = ev.get("verification_url", ev["source_url"])
        snap = fetcher.get_json(url, phase="verify") if api else fetcher.get(url, phase="verify")
        if not snap.ok:
            errors += 1
            rows.append(("error", org, claim["field"], snap.status))
            continue
        span = ev["claim_span"]
        ok = span_present(snap.text(), span)
        found += ok
        drift += not ok
        if not ok:
            rows.append(("drift", org, claim["field"], span[:80]))
    n = len(sample)
    print(json.dumps({"sampled": n, "span_refound": found, "drift_or_changed": drift, "fetch_errors": errors,
                      "refound_rate": round(found / max(1, n - errors), 3)}, ensure_ascii=False))
    for row in rows[:20]:
        print("  ", row)
    fetcher.close()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    main()
