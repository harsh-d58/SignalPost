"""Refresh: compare this run's profile with the previous one and emit typed, evidenced changes.

* Claims are matched on (family, key) — a stable identity of the fact, independent of value.
* Same snapshot => same claim IDs => zero changes (idempotent; tested).
* A family that could not be read this run (failed/blocked/budget) is `not_compared`: prior values are
  carried forward with `stale_since`, never reported as removed.
* Prior evidence is preserved: carried-forward claims keep their original evidence records.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .job_dates import job_expired, parse_job_date

CHANGE_TYPES = {
    ("leadership", "added"): "new_role", ("leadership", "removed"): "ended_role", ("leadership", "changed"): "changed_role",
    ("locations", "added"): "new_location", ("locations", "removed"): "closed_location", ("locations", "changed"): "changed_location",
    ("jobs", "added"): "new_job", ("jobs", "removed"): "closed_job", ("jobs", "changed"): "changed_job",
    ("financials", "added"): "new_filing", ("financials", "changed"): "restated_value", ("financials", "removed"): "removed_filing_value",
    ("activity", "added"): "new_activity", ("activity", "removed"): "aged_out_activity",
    ("website", "added"): "new_website", ("website", "removed"): "website_removed", ("website", "changed"): "website_change",
    ("status", "added"): "status_change", ("status", "changed"): "status_change", ("status", "removed"): "status_change",
    ("description", "changed"): "changed_description", ("description", "added"): "new_description",
    ("social_profiles", "added"): "new_profile", ("social_profiles", "removed"): "removed_profile", ("social_profiles", "changed"): "changed_profile",
}
UNREADABLE = {"failed", "blocked", "ambiguous"}
FIELD_TYPES = {"business_address": "address_change", "postal_address": "address_change", "legal_name": "name_change",
               "employees": "employee_count_change", "share_capital": "capital_change", "legal_form": "legal_form_change",
               "industry_code": "industry_change", "official_website": "website_change", "ceo": "ceo_change"}
MINOR = {"employee_count_change", "aged_out_activity", "changed_location"}


def load_previous(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    p = Path(path)
    if p.is_dir():
        p = next((p / n for n in ("envelopes.jsonl", "profiles.jsonl") if (p / n).exists()), p / "envelopes.jsonl")
    if not p.exists():
        return {}
    out = {}
    import gzip
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                out[row["organisation_number"]] = row
    return out


def _index(envelope: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(c["family"], c.get("key") or c["field"]): c for c in envelope.get("claims", []) if c.get("availability", "available") == "available"}


def diff(previous: dict[str, Any] | None, current: dict[str, Any], *, detected_at: str) -> tuple[list[dict], dict[str, Any]]:
    """Return (changes, refresh_meta) and mutate `current` to carry forward unreadable families."""
    if not previous:
        for claim in current.get("claims", []):
            claim["first_seen"] = claim["last_seen"] = detected_at
            claim["times_seen"] = 1
        return [], {"mode": "baseline", "previous_run_id": None, "compared_families": [], "not_compared": []}
    prev_claims = _index(previous)
    cur_claims = _index(current)
    prev_evidence = {e["id"]: e for e in previous.get("evidence", [])}
    states = current.get("availability", {})
    incomplete = current.get("incomplete_families", {})
    closed = current.get("closed_jobs", {})
    prev_started = previous.get("run", {}).get("started_at") or previous.get("run", {}).get("completed_at")
    for key, claim in cur_claims.items():
        old = prev_claims.get(key)
        claim["first_seen"] = (old.get("first_seen") or prev_started) if old else detected_at
        claim["last_seen"] = detected_at  # carried-forward (stale) claims keep their own last_seen
        claim["times_seen"] = (int(old.get("times_seen") or 1) + 1) if old else 1
    for claim in current.get("claims", []):  # claims sharing a key with an indexed claim inherit its history
        if claim.get("availability", "available") == "available" and "times_seen" not in claim:
            twin = cur_claims.get((claim["family"], claim.get("key") or claim["field"])) or {}
            for f in ("first_seen", "last_seen", "times_seen"):
                claim[f] = twin.get(f, detected_at if f != "times_seen" else 1)
    changes: list[dict] = []
    not_compared: list[str] = []
    compared: list[str] = []
    families = sorted({f for f, _ in prev_claims} | {f for f, _ in cur_claims})
    for family in families:
        state = (states.get(family) or {}).get("state")
        expired = set(closed) if family == "jobs" else set()
        if family == "jobs":
            observed = parse_job_date(detected_at)
            for (fam, key), claim in prev_claims.items():
                if fam != "jobs" or not isinstance(claim.get("value"), dict):
                    continue
                deadline = parse_job_date(claim["value"].get("expires"))
                if deadline is not None and observed is not None and job_expired(deadline, observed):
                    expired.add(key)
        if state in UNREADABLE or family in incomplete or ((states.get(family) or {}).get("reason", "").startswith("request budget")):
            not_compared.append(family)
            # carry forward last supported values with their original evidence
            for (fam, key), claim in prev_claims.items():
                if fam == family and (fam, key) not in cur_claims:
                    if family == "jobs" and key in expired:
                        continue
                    if family == "jobs" and any("pam-stilling-feed.nav.no" in prev_evidence.get(eid, {}).get("source_url", "") for eid in claim.get("evidence_ids", [])):
                        continue  # NAV requires current active status; an unreadable ad cannot remain published
                    carried = dict(claim)
                    carried["stale_since"] = claim.get("stale_since") or detected_at
                    carried["availability"] = "available"
                    current["claims"].append(carried)
                    for eid in claim.get("evidence_ids", []):
                        if eid in prev_evidence and all(e["id"] != eid for e in current["evidence"]):
                            current["evidence"].append(prev_evidence[eid])
            # Compare positively observed values, but never infer removals from an incomplete crawl.
            if state in UNREADABLE and not expired and not any(f == family for f, _ in cur_claims):
                continue
        compared.append(family)
        keys = {k for f, k in prev_claims if f == family} | {k for f, k in cur_claims if f == family}
        for key in sorted(keys):
            old = prev_claims.get((family, key))
            new = cur_claims.get((family, key))
            if old and new:
                if all(old.get(k) == new.get(k) for k in ("value", "unit", "period")):
                    continue
                kind = "changed"
            elif new:
                kind = "added"
            else:
                if (family in incomplete or state in UNREADABLE) and key not in expired:
                    continue
                kind = "removed"
            if family == "activity" and kind == "removed":
                continue  # activity items age out of the window; not a material change
            if family == "financials" and kind == "removed" and any(f == "financials" for f, _ in cur_claims):
                continue  # older filing years roll out of the API's 3-year window; not a material change
            ref = new or old
            changes.append({
                "id": f"chg-{ref['id']}-{kind}",
                "type": (ctype := FIELD_TYPES.get(ref["field"]) if kind == "changed" else None) or CHANGE_TYPES.get((family, kind), f"{kind}_value"),
                "material": (ctype or CHANGE_TYPES.get((family, kind), "")) not in MINOR,
                "family": family,
                "field": ref["field"],
                "key": key,
                "label": ref.get("label"),
                "previous": old.get("value") if old else None,
                "current": new.get("value") if new else None,
                "previous_unit": old.get("unit") if old else None,
                "current_unit": new.get("unit") if new else None,
                "previous_period": old.get("period") if old else None,
                "current_period": new.get("period") if new else None,
                "evidence_ids": (new or {}).get("evidence_ids") or (closed.get(key, {}).get("evidence_ids", []) if family == "jobs" else []),
                "previous_evidence_ids": (old or {}).get("evidence_ids") or [],
                "detected_at": detected_at,
            })
    meta = {
        "mode": "refresh",
        "previous_run_id": previous.get("run", {}).get("run_id"),
        "previous_completed_at": previous.get("run", {}).get("completed_at"),
        "compared_families": compared,
        "not_compared": not_compared,
        "change_count": len(changes),
    }
    return changes, meta
