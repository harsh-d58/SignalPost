"""Source attribution and factual accuracy probes with offline fixtures."""

import hashlib
import json
from pathlib import Path

import pytest

from signalpost.model import ProfileBuilder
from signalpost.registry import accounts_claims
from signalpost.web import _news, _site_jobs
from test_improvement_cases import BASE, DATE, NAME, ORG, OTHER, Pages, offline_clock, page, snapshot, verified


@pytest.mark.parametrize("employer, deadline, body, expected", [
    pytest.param({"identifier": ORG, "name": NAME}, "2026-12-01", "", True, id="exact-employer-active"),
    pytest.param({"identifier": OTHER, "name": NAME}, "2026-12-01", "", False, id="foreign-id-overrides-name"),
    pytest.param({"name": "Fjord Marine Service ASA"}, "2026-12-01", "", False, id="different-legal-form"),
    pytest.param({"name": "Fjord Marine Service Holding AS"}, "2026-12-01", "", False, id="parent-employer"),
    pytest.param({"identifier": ORG}, "2026-11-11T01:00:00+02:00", "", False, id="expired-offset"),
    pytest.param({"identifier": ORG}, "2026-11-11T03:00:00+02:00", "", True, id="valid-offset"),
    pytest.param({"identifier": ORG}, None, "<p>Applications closed. This vacancy is no longer available.</p>", False, id="closed-page-recent-metadata"),
])
def test_website_vacancy_publication(employer, deadline, body, expected):
    node = {"@type": "JobPosting", "title": "Marine engineer", "datePosted": DATE,
            "directApply": True, "hiringOrganization": employer}
    if deadline is not None:
        node["validThrough"] = deadline
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, verified(page("/jobs/engineer", nodes=[node], body=body)))
    assert bool(pb.family_claims("jobs")) is expected


@pytest.mark.parametrize("path, node, body, expected", [
    pytest.param("/news/opening", {"datePublished": DATE}, "", True, id="explicit-publication"),
    pytest.param("/news/opening", {"dateModified": DATE}, "", False, id="modification-only"),
    pytest.param("/news/opening", {"datePublished": DATE, "publisher": {"identifier": OTHER}}, "", False, id="foreign-publisher"),
    pytest.param("/products/engine", {"datePublished": DATE}, "", False, id="product-page"),
    pytest.param("/news/opening", None,
                 f'<article><h1>New office opens</h1><time class="unpublished" datetime="{DATE}">{DATE}</time></article>',
                 False, id="unpublished-class"),
    pytest.param("/news/opening", None,
                 f'<article><h1>New office opens</h1><time itemprop="datePublished" datetime="{DATE}">{DATE}</time></article>',
                 True, id="html-publication-marker"),
    pytest.param("/news/opening", {"datePublished": DATE, "publisher": {"name": "Fjord Marine Service ASA"}},
                 "", False, id="publisher-different-legal-form"),
])
def test_company_article_publication(path, node, body, expected):
    nodes = [] if node is None else [{"@type": "NewsArticle", "headline": "New office opens", **node}]
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(), verified(page(path, nodes=nodes, body=body)), BASE + "/")
    assert bool(pb.family_claims("activity")) is expected


@pytest.mark.parametrize("changes, expected", [
    pytest.param({}, True, id="matching-account"),
    pytest.param({"value": 5001}, False, id="changed-value"),
    pytest.param({"unit": "EUR"}, False, id="changed-currency"),
    pytest.param({"period": {"from": "2024-01-01", "to": "2024-12-31"}}, False, id="changed-period"),
    pytest.param({"note": "account_type=KONSERN"}, False, id="changed-scope"),
    pytest.param({"field": "cash"}, False, id="changed-field"),
])
def test_snapshot_audit_binds_claim_to_account_locator(tmp_path, monkeypatch, changes, expected):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from snapshot_audit import audit

    period = {"from": "2025-01-01", "to": "2025-12-31"}
    original = [{"organisasjonsnummer": ORG, "regnskapsperiode": {"fraDato": period["from"], "tilDato": period["to"]},
                 "valuta": "NOK", "regnskapstype": "SELSKAP", "eiendeler": {"sumEiendeler": 5000}}]
    raw = json.dumps(original).encode()
    (tmp_path / "account.json").write_bytes(raw)
    evidence = {"id": "ev", "snapshot_id": "source", "claim_span": '"sumEiendeler": 5000',
                "locator": {"type": "json_pointer", "pointer": "/0/eiendeler/sumEiendeler", "value": 5000,
                            "record_pointer": "/0", "organisation_number": ORG, "currency": "NOK", "period": period}}
    claim = {"id": "claim", "family": "financials", "field": "total_assets", "value": 5000, "unit": "NOK",
             "period": period, "note": "account_type=SELSKAP", "evidence_ids": ["ev"], **changes}
    envelope = {"organisation_number": ORG, "claims": [claim], "evidence": [evidence],
                "source_snapshots": [{"id": "source", "retention": "minimized_json",
                                      "object": {"path": "account.json", "sha256": hashlib.sha256(raw).hexdigest()}}]}
    (tmp_path / "envelopes.jsonl").write_text(json.dumps(envelope) + "\n", encoding="utf-8")
    assert audit(tmp_path)["passed"] is expected


def test_equal_account_values_keep_separate_record_locators():
    period = {"fraDato": "2025-01-01", "tilDato": "2025-12-31"}
    records = [
        {"organisasjonsnummer": ORG, "regnskapstype": scope, "regnskapsperiode": period,
         "valuta": "NOK", "eiendeler": {"sumEiendeler": 5000}}
        for scope in ("SELSKAP", "KONSERN")
    ]
    pb = ProfileBuilder(ORG)
    accounts_claims(pb, snapshot(json.dumps(records), "https://data.brreg.no/regnskapsregisteret/regnskap/" + ORG))
    claims = {c.note: c for c in pb.family_claims("financials")}
    for index, scope in enumerate(("SELSKAP", "KONSERN")):
        claim = claims[f"account_type={scope}"]
        evidence = pb.evidence[claim.evidence_ids[0]]
        assert evidence.locator["record_pointer"] == f"/{index}"

@pytest.mark.parametrize("field", ["audit_status", "accounting_rules"])
@pytest.mark.parametrize("mutate", [False, True])
def test_account_metadata_claims_are_bound_to_record(tmp_path, monkeypatch, field, mutate):
    from signalpost.evidence import SnapshotStore
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from snapshot_audit import audit
    records = [{"organisasjonsnummer": ORG, "regnskapstype": "SELSKAP", "valuta": "NOK",
                "regnskapsperiode": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
                "revisjon": {"ikkeRevidertAarsregnskap": True},
                "regnkapsprinsipper": {"regnskapsregler": "smaa"}}]
    snap = snapshot(json.dumps(records), "https://data.brreg.no/regnskapsregisteret/regnskap/" + ORG)
    pb = ProfileBuilder(ORG)
    accounts_claims(pb, snap)
    store = SnapshotStore(tmp_path)
    store.capture(snap)
    evidence = [e.to_dict() for e in pb.evidence.values()]
    sources = [store.bind(e) for e in evidence]
    claims = [c.to_dict() for c in pb.family_claims("financials") if c.field == field]
    if mutate:
        claims[0]["value"] = "unsupported replacement"
    env = {"organisation_number": ORG, "claims": claims, "evidence": evidence, "source_snapshots": sources}
    (tmp_path / "envelopes.jsonl").write_text(json.dumps(env) + "\n", encoding="utf-8")
    result = audit(tmp_path)
    assert result["passed"] is not mutate
    assert result["financial_fields"][field]["invalid" if mutate else "verified"] == 1

@pytest.mark.parametrize("mutation", [None, "year", "period", "copy", "owner"])
def test_filing_history_binds_source_entity_and_claim(tmp_path, monkeypatch, mutation):
    from signalpost.evidence import SnapshotStore
    from signalpost.registry import history_claims, HISTORY_URL
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from snapshot_audit import audit
    snap = snapshot('["2024", "2025"]', HISTORY_URL.format(org=ORG))
    pb = ProfileBuilder(ORG)
    history_claims(pb, snap)
    store = SnapshotStore(tmp_path)
    store.capture(snap)
    evidence = [e.to_dict() for e in pb.evidence.values()]
    sources = [store.bind(e) for e in evidence]
    claim = pb.family_claims("financials")[0].to_dict()
    if mutation == "year":
        claim["value"]["year"] = "2023"
    elif mutation == "period":
        claim["period"]["to"] = "2025-11-30"
    elif mutation == "copy":
        claim["value"]["official_copy"] = claim["value"]["official_copy"].replace(ORG, OTHER)
    env = {"organisation_number": OTHER if mutation == "owner" else ORG, "claims": [claim],
           "evidence": evidence, "source_snapshots": sources}
    (tmp_path / "envelopes.jsonl").write_text(json.dumps(env) + "\n", encoding="utf-8")
    result = audit(tmp_path)
    if mutation == "owner":
        assert not result["passed"] and result["invalid_history_claims"] == 1
    elif mutation:
        assert not result["passed"] and result["invalid_history_claims"] == 1
    else:
        assert result["passed"] and result["history_claims_verified"] == 1
