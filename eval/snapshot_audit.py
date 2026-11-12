"""Audit retained evidence offline. Excerpt-only artifacts are reported separately.

Usage: uv run python eval/snapshot_audit.py out-run --output report.json
This checks integrity and source locators; it does not estimate company precision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from verify_evidence import compact, span_present
from signalpost.registry import FIN_FIELDS, HISTORY_URL, HISTORY_PDF

ACCOUNT_FIELDS = {field: "/" + "/".join(path) for field, _, path in FIN_FIELDS}


def pointer(value, path):
    for key in path.split("/")[1:]:
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def audit(root: Path) -> dict:
    root = root.resolve()
    counts = {"evidence": 0, "source_locators_verified": 0, "excerpt_artifacts_verified": 0,
              "missing_references": 0, "invalid_objects": 0, "invalid_locators": 0,
              "history_claims_verified": 0, "history_claims_unverified": 0, "invalid_history_claims": 0,
              "account_claims_verified": 0, "account_claims_unverified": 0, "invalid_account_claims": 0}
    fields = defaultdict(lambda: {"verified": 0, "unverified": 0, "invalid": 0})
    errors = []
    objects = {}
    supports = {}
    for line in (root / "envelopes.jsonl").read_text(encoding="utf-8").splitlines():
        env = json.loads(line)
        records = {s["id"]: s for s in env.get("source_snapshots", [])}
        account_evidence = {}
        history_evidence = {}
        invalid_history_evidence = set()
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
                        source_value = pointer(data, locator["pointer"])
                        ok = source_value == locator["value"]
                        if locator.get("record_pointer"):
                            if isinstance(source_value, (int, float)):
                                ok &= type(source_value) in (int, float) and type(locator["value"]) in (int, float)
                            rec = pointer(data, locator["record_pointer"])
                            period = rec.get("regnskapsperiode") or {}
                            owner = rec.get("organisasjonsnummer") or (rec.get("virksomhet") or {}).get("organisasjonsnummer")
                            ok &= (not owner or str(owner) == locator["organisation_number"])
                            ok &= (rec.get("valuta") or None) == locator.get("currency")
                            ok &= {"from": period.get("fraDato"), "to": period.get("tilDato")} == locator["period"]
                            scope = rec.get("regnskapstype")
                            if "account_type" in locator:
                                ok &= bool(scope) and str(scope).upper() == locator["account_type"]
                            if ok:
                                account_evidence[ev["id"]] = (locator, owner, scope)
                        if locator.get("parent_pointer"):
                            ok &= str(pointer(data, locator["parent_pointer"])) == locator["organisation_number"]
                    else:
                        key = (relative, ev["claim_span"])
                        if key not in supports:
                            supports[key] = compact(ev["claim_span"]) in compact_text or span_present(text, ev["claim_span"])
                        ok = supports[key]
                    metric = "source_locators_verified"
                if ok and record["retention"] != "excerpt_only" and ev.get("extraction_method") == "regnskapsregisteret_kopi_api:aar":
                    expected_url = HISTORY_URL.format(org=env["organisation_number"])
                    if (ev.get("source_url") == expected_url and record.get("requested_url") == expected_url
                            and record.get("final_url") == expected_url and record.get("status") == 200
                            and isinstance(data, list)):
                        history_evidence[ev["id"]] = {str(y) for y in data if type(y) in (str, int) and len(str(y)) == 4 and str(y).isascii() and str(y).isdigit()}
                    else:
                        invalid_history_evidence.add(ev["id"])
                counts[metric if ok else "invalid_locators"] += 1
                if not ok:
                    errors.append([env["organisation_number"], ev["id"], "locator does not match retained source"])
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                counts["invalid_locators"] += 1
                errors.append([env["organisation_number"], ev["id"], str(exc)])
        for claim in env.get("claims", []):
            if claim["family"] != "financials" or claim.get("availability", "available") != "available":
                continue
            if claim["field"] == "filed_annual_accounts":
                if any(eid in invalid_history_evidence for eid in claim.get("evidence_ids", [])):
                    counts["invalid_history_claims"] += 1
                    fields[claim["field"]]["invalid"] += 1
                    errors.append([env["organisation_number"], claim["id"], "filing history source identity mismatch"])
                    continue
                sources = [history_evidence[eid] for eid in claim.get("evidence_ids", []) if eid in history_evidence]
                if not sources:
                    counts["history_claims_unverified"] += 1
                    fields[claim["field"]]["unverified"] += 1
                    continue
                value = claim.get("value")
                year = value.get("year") if isinstance(value, dict) else None
                valid = (isinstance(year, str) and all(year in years for years in sources)
                         and value.get("official_copy") == HISTORY_PDF.format(org=env["organisation_number"], year=year)
                         and claim.get("period") == {"from": f"{year}-01-01", "to": f"{year}-12-31"}
                         and claim.get("unit") is None)
                counts["history_claims_verified" if valid else "invalid_history_claims"] += 1
                fields[claim["field"]]["verified" if valid else "invalid"] += 1
                if not valid:
                    errors.append([env["organisation_number"], claim["id"], "filing year, owner, copy URL or period does not match history source"])
                continue
            candidates = [account_evidence[eid] for eid in claim.get("evidence_ids", []) if eid in account_evidence]
            if not candidates:
                counts["account_claims_unverified"] += 1
                fields[claim["field"]]["unverified"] += 1
                continue
            verified = False
            for locator, owner, scope in candidates:
                field_path = ACCOUNT_FIELDS.get(claim["field"])
                expected = locator["value"]
                numeric = claim["field"] in ACCOUNT_FIELDS
                if claim["field"] == "audit_status" and isinstance(expected, dict):
                    field_path = "/revisjon"
                    expected = "not audited" if expected.get("ikkeRevidertAarsregnskap") or expected.get("fravalgRevisjon") else "audited"
                elif claim["field"] == "accounting_rules":
                    field_path = "/regnkapsprinsipper/regnskapsregler"
                scope_matches = (claim.get("note") == f"account_type={str(scope).upper()}" if numeric else
                                 claim.get("key") == f"{'audit' if claim['field'] == 'audit_status' else 'rules'}:{str(scope).upper()}:{locator['period']['to']}") if scope else "account_type" not in locator
                valid = (
                    env["organisation_number"] == locator["organisation_number"]
                    and (not owner or str(owner) == env["organisation_number"])
                    and (locator["pointer"] == locator["record_pointer"] + field_path if field_path else False)
                    and (not numeric or type(claim["value"]) in (int, float)) and claim["value"] == expected
                    and claim.get("unit") == (locator.get("currency") if numeric else None)
                    and claim.get("period") == locator["period"]
                    and scope_matches
                )
                if not valid:
                    counts["invalid_account_claims"] += 1
                    fields[claim["field"]]["invalid"] += 1
                    errors.append([env["organisation_number"], claim["id"], "claim does not match account record"])
                    break
                verified |= bool(owner and scope)
            else:
                # Evidence without an explicit owner or scope cannot verify attribution.
                counts["account_claims_verified" if verified else "account_claims_unverified"] += 1
                fields[claim["field"]]["verified" if verified else "unverified"] += 1
    return {**counts, "financial_fields": dict(sorted(fields.items())), "unique_objects": len(objects), "passed": not any(counts[k] for k in ("missing_references", "invalid_objects", "invalid_locators", "invalid_account_claims", "invalid_history_claims")),
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
