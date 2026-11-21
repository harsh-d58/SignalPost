"""Offline differential checks. Run with python -m eval.diagnostics.audit_core_rules RUN."""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from eval.diagnostics.test_identity_and_article_boundaries import snapshot
from signalpost.model import ProfileBuilder
from signalpost.refresh import diff
from signalpost.registry import accounts_claims
from signalpost.web import extract_company_owned, visit_site


def audit(run):
    counts = Counter()
    conflicts = []
    for line in (run / "envelopes.jsonl").open(encoding="utf-8"):
        env = json.loads(line)
        counts["companies"] += 1
        current = [c for c in env["claims"] if c.get("availability", "available") == "available" and not c.get("stale_since")]
        previous = dict(env, claims=current)
        replay = copy.deepcopy(previous)
        changes, _ = diff(previous, replay, detected_at=env["run"]["completed_at"])
        counts["identical_replay_changes"] += len(changes)
        periods = {}
        for claim in current:
            period = claim.get("period")
            if claim.get("note") == "account_type=SELSKAP" and period and period.get("to"):
                periods.setdefault(period["to"][:4], set()).add((period.get("from"), period["to"]))
        for claim in current:
            if claim["field"] != "filed_annual_accounts":
                continue
            counts["filing_history_claims"] += 1
            dates = periods.get(claim["value"]["year"])
            if dates:
                counts["years_with_comparable_company_accounts"] += 1
                stated = claim.get("period") or {}
                if stated and (stated.get("from"), stated.get("to")) not in dates:
                    conflicts.append([env["organisation_number"], claim["value"]["year"], sorted(dates)])
    return {**counts, "conflicting_years": len(conflicts), "companies_with_conflicts": len({c[0] for c in conflicts}),
            "first_conflicts": conflicts[:5]}


def publisher_probe():
    url = "https://group.example.no/"
    body = ('<title>Parent Group AS</title><meta property="og:site_name" content="Parent Group AS">'
            '<meta property="og:title" content="OTIS AS"><main><p>Our customer OTIS AS hired '
            'Parent Group AS to provide consultancy and project management services. '
            'This case study describes the services our team delivered.</p></main>')

    class Fetch:
        def get(self, target, **kwargs):
            return snapshot(target, body) if target == url else snapshot(target, "", 404)

    pb = ProfileBuilder("919419105")
    fetch = Fetch()
    with patch("signalpost.web.host_is_public", return_value=True):
        visit = visit_site(fetch, url, "registry_declared", pb.org, {}, "OTIS AS", set())
        extract_company_owned(pb, fetch, visit, "OTIS AS", defer_enrichment=True)
    return {"published_customer_host": bool(pb.family_claims("website")), "reason": visit.reason}


def accounts_probe():
    pb = ProfileBuilder("919419105")
    record = {"organisasjonsnummer": pb.org, "valuta": "NOK", "regnskapsperiode": {
        "fraDato": "2025-01-01", "tilDato": "2025-12-31"}, "eiendeler": {"sumEiendeler": 123},
        "revisjon": {"ikkeRevidertAarsregnskap": None, "fravalgRevisjon": None}}
    response = snapshot("https://data.brreg.no/regnskapsregisteret/regnskap/" + pb.org, json.dumps([record]))
    accounts_claims(pb, response)
    return [(c.field, c.value, c.note) for c in pb.family_claims("financials")]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps({"runs": {str(run): audit(run) for run in args.runs}, "publisher": publisher_probe(),
                      "missing_scope_and_audit_flags": accounts_probe()}, indent=2))
