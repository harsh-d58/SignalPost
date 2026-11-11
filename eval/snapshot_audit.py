"""Audit retained evidence offline. Excerpt-only artifacts are reported separately.

Usage: uv run python eval/snapshot_audit.py out-run --output report.json
This checks integrity and source locators; it does not estimate company precision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from verify_evidence import compact, span_present


def pointer(value, path):
    for key in path.split("/")[1:]:
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def audit(root: Path) -> dict:
    root = root.resolve()
    counts = {"evidence": 0, "source_locators_verified": 0, "excerpt_artifacts_verified": 0,
              "missing_references": 0, "invalid_objects": 0, "invalid_locators": 0}
    errors = []
    objects = {}
    supports = {}
    for line in (root / "envelopes.jsonl").read_text(encoding="utf-8").splitlines():
        env = json.loads(line)
        records = {s["id"]: s for s in env.get("source_snapshots", [])}
        for ev in env.get("evidence", []) + env.get("prior_evidence", []):
            counts["evidence"] += 1
            record = records.get(ev.get("snapshot_id"))
            if not record:
                counts["missing_references"] += 1
                continue
            obj = record.get("object") or {}
            try:
                relative = obj["path"]
                if relative not in objects:
                    path = (root / relative).resolve()
                    if not path.is_relative_to(root):
                        raise ValueError("unsafe snapshot path")
                    raw = path.read_bytes()
                    decoded = raw.decode("utf-8")
                    objects[relative] = (decoded, json.loads(raw), compact(decoded), hashlib.sha256(raw).hexdigest())
                text, data, compact_text, digest = objects[relative]
                if digest != obj["sha256"]:
                    raise ValueError("digest mismatch")
            except (OSError, KeyError, ValueError) as exc:
                counts["invalid_objects"] += 1
                errors.append([env["organisation_number"], ev["id"], str(exc)])
                continue
            try:
                if record["retention"] == "excerpt_only":
                    ok = data["claim_span"] == ev["claim_span"] and data["content_sha256"] == ev["content_sha256"]
                    metric = "excerpt_artifacts_verified"
                else:
                    locator = ev.get("locator", {})
                    if locator.get("type") == "json_pointer":
                        ok = pointer(data, locator["pointer"]) == locator["value"]
                        if locator.get("record_pointer"):
                            rec = pointer(data, locator["record_pointer"])
                            period = rec.get("regnskapsperiode") or {}
                            owner = rec.get("organisasjonsnummer") or (rec.get("virksomhet") or {}).get("organisasjonsnummer")
                            ok &= (not owner or str(owner) == locator["organisation_number"])
                            ok &= (rec.get("valuta") or None) == locator.get("currency")
                            ok &= {"from": period.get("fraDato"), "to": period.get("tilDato")} == locator["period"]
                        if locator.get("parent_pointer"):
                            ok &= str(pointer(data, locator["parent_pointer"])) == locator["organisation_number"]
                    else:
                        key = (relative, ev["claim_span"])
                        if key not in supports:
                            supports[key] = compact(ev["claim_span"]) in compact_text or span_present(text, ev["claim_span"])
                        ok = supports[key]
                    metric = "source_locators_verified"
                counts[metric if ok else "invalid_locators"] += 1
                if not ok:
                    errors.append([env["organisation_number"], ev["id"], "locator does not match retained source"])
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                counts["invalid_locators"] += 1
                errors.append([env["organisation_number"], ev["id"], str(exc)])
    return {**counts, "unique_objects": len(objects), "passed": not any(counts[k] for k in ("missing_references", "invalid_objects", "invalid_locators")),
            "errors": errors[:30], "limitation": "Excerpt integrity does not independently establish full-page support or exact-company precision."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.run)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    raise SystemExit(0 if report["passed"] else 1)
