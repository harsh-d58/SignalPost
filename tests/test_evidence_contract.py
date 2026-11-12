import copy
import hashlib
import io
import json
from pathlib import Path

import pytest

from signalpost.bulk import _json_array
from signalpost.evidence import SnapshotStore, instant
from signalpost.http import Snapshot
from signalpost.jobs import JobFeed
from signalpost.model import Evidence, ProfileBuilder
from signalpost.pipeline import Runner
from signalpost.registry import accounts_claims, load_bulk, roles_claims
from signalpost.refresh import diff

ORG = "923609016"
AT = "2026-11-09T00:00:00Z"


def source(value, url="https://data.brreg.no/regnskapsregisteret/regnskap/" + ORG):
    body = json.dumps(value).encode()
    return Snapshot(url, url, 200, AT, body=body, sha256=hashlib.sha256(body).hexdigest())


def runner(root, **kw):
    return Runner([ORG], out_dir=root, run_id="test", bulk=None, previous=None, max_requests=2000,
                  max_minutes=45, max_cost=10, workers=2, job_days=7, web=False, log=lambda *_: None, **kw)


def test_snapshot_dedup_privacy_and_integrity(tmp_path):
    store = SnapshotStore(tmp_path)
    snap = source({"navn": "Example AS", "person": {"foedselsdato": "1970-01-01", "navn": "Person"}, "epostadresse": "private@example.no"})
    store.capture(snap)
    ev = Evidence(snap.url, "official_registry", AT, snap.sha256, '"navn": "Example AS"', "json").to_dict()
    first = store.bind(ev)
    assert first == store.bind(ev)
    body = (tmp_path / first["object"]["path"]).read_bytes()
    assert b"1970" not in body and b"private@" not in body
    assert hashlib.sha256(body).hexdigest() == first["object"]["sha256"]
    assert first["content_sha256"] != first["object"]["sha256"]
    (tmp_path / first["object"]["path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        store.import_record(first, tmp_path)


def test_company_pages_keep_only_excerpt_and_tokens_never_persist(tmp_path):
    store = SnapshotStore(tmp_path)
    snap = source({"public": "Example AS", "secret": "private contact"}, "https://example.no/about")
    store.capture(snap)
    ev = Evidence(snap.url, "company_owned", AT, snap.sha256, "Example AS", "html").to_dict()
    record = store.bind(ev)
    assert record["retention"] == "excerpt_only"
    assert "private contact" not in (tmp_path / record["object"]["path"]).read_text()
    store.capture(source({"token": "secret"}, "https://pam-stilling-feed.nav.no/api/publicToken"))
    assert all("publicToken" not in k[1] for k in store.records)


@pytest.mark.parametrize("suffix,content", [(".jsonl", '{"organisasjonsnummer":"923609016","navn":"Frozen AS"}\n'),
                                           (".json", ' [ {"organisasjonsnummer":"923609016","navn":"Frozen AS"} ]'),
                                           (".csv", 'organisasjonsnummer,navn\n923609016,Frozen AS\n')])
def test_frozen_input_formats(tmp_path, suffix, content):
    path = tmp_path / ("snapshot" + suffix)
    path.write_text(content, encoding="utf-8")
    rows, meta = load_bulk(path, [ORG])
    assert rows[ORG]["navn"] == "Frozen AS"
    assert meta["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_identity_authoritative_and_missing_anchor_explicit(tmp_path, monkeypatch):
    path = tmp_path / "registry.jsonl"
    path.write_text(json.dumps({"organisasjonsnummer": ORG, "navn": "Frozen AS"}) + "\n")
    r = runner(tmp_path / "run", registry_snapshot=str(path), registry_snapshot_at=AT)
    monkeypatch.setattr("signalpost.pipeline.fetch_entities", lambda *_: pytest.fail("live identity must not override frozen identity"))
    monkeypatch.setattr("signalpost.pipeline.fetch_activity", lambda *_: ({}, {}, []))
    monkeypatch.setattr(r, "company", lambda *_: None)
    monkeypatch.setattr(r, "tail_pass", lambda *_: None)
    try:
        report = r.run()
        env = json.loads((r.out_dir / "envelopes.jsonl").read_text())
        assert env["name"] == "Frozen AS"
        assert report["validation"]["passed"]
        assert env["source_snapshots"][0]["provenance"]["input_sha256"] == report["registry_snapshot"]["sha256"]
    finally:
        r.finished.set()
        r.fetcher.close()


def test_cutoff_suppresses_ineligible_claims(tmp_path):
    r = runner(tmp_path, evidence_cutoff="2026-11-08T23:00:00Z")
    snap = source([{"eiendeler": {"sumEiendeler": 10}, "valuta": "NOK"}])
    try:
        r.store.capture(snap)
        accounts_claims(r.builders[ORG], snap)
        env = r.envelope(ORG, AT, None)
        assert not any(c.get("availability") == "available" for c in env["claims"])
        assert env["availability"]["financials"]["state"] == "failed"
    finally:
        r.fetcher.close()


def test_source_failure_refresh_carries_snapshot_to_new_directory(tmp_path):
    old = runner(tmp_path / "old")
    new = runner(tmp_path / "new")
    try:
        snap = source([{"eiendeler": {"sumEiendeler": 0}, "valuta": "NOK"}])
        old.store.capture(snap)
        accounts_claims(old.builders[ORG], snap)
        previous = old.envelope(ORG, AT, None)
        new.previous_path = str(old.out_dir)
        env = new.envelope(ORG, "2026-11-10T00:00:00Z", previous)
        assert not env["changes"]
        assert any(c.get("stale_since") and c["value"] == 0 for c in env["claims"])
        assert all((new.out_dir / s["object"]["path"]).exists() for s in env["source_snapshots"])
    finally:
        old.fetcher.close()
        new.fetcher.close()


def test_nav_default_has_no_network_without_credentials(monkeypatch):
    monkeypatch.delenv("NAV_FEED_TOKEN", raising=False)
    feed = JobFeed(object())
    feed._run()
    assert feed.done.is_set() and feed.error.startswith("blocked:")
    assert not feed.ads


@pytest.mark.parametrize("body", ['[{},]', '[{}] garbage', '[{}', '[{} {}]'])
def test_bulk_invalid_completion_is_not_absence(body):
    with pytest.raises(ValueError):
        list(_json_array(io.StringIO(body)))


def test_conflicting_role_owner_abstains():
    pb = ProfileBuilder(ORG)
    roles_claims(pb, source({"organisasjonsnummer": "984661185", "rollegrupper": []}))
    assert pb.families["leadership"].state == "ambiguous"
    assert not pb.claims


def test_history_name_locator_points_inside_actual_list(tmp_path):
    from signalpost.registry import entity_claims
    entity = {"organisasjonsnummer": ORG, "navn": "Current AS", "historiskeNavn": [{"navn": "Old AS", "fraDato": "2020-01-01", "tilDato": "2021-01-01"}]}
    snap = source({"_embedded": {"enheter": [entity]}})
    pb = ProfileBuilder(ORG)
    entity_claims(pb, entity, retrieved_at=AT, source_class="official_registry", method="fixture", snapshot=snap)
    ev = next(e for e in pb.evidence.values() if e.extraction_method.endswith(":historiskeNavn"))
    assert ev.locator["pointer"] == "/_embedded/enheter/0/historiskeNavn/0"
    assert ev.locator["value"] == entity["historiskeNavn"][0]
    assert not ev.claim_span.startswith('"historiskeNavn"')


@pytest.mark.parametrize("address_key", ["forretningsadresse", "postadresse"])
def test_municipality_locator_points_to_address(address_key):
    from signalpost.registry import entity_claims
    entity = {"organisasjonsnummer": ORG, "navn": "Current AS", address_key: {"kommune": "OSLO"}}
    pb = ProfileBuilder(ORG)
    entity_claims(pb, entity, retrieved_at=AT, source_class="official_registry", method="fixture", snapshot=source(entity))
    ev = next(e for e in pb.evidence.values() if e.extraction_method.endswith(":kommune"))
    assert ev.locator["pointer"] == f"/{address_key}/kommune"
    assert ev.locator["value"] == "OSLO"


def test_csv_and_json_addresses_have_identical_values():
    from signalpost.registry import fmt_address
    tail = {"postnummer": "0177", "poststed": "OSLO"}
    assert fmt_address({**tail, "adresse": ["c/o Example\nStreet 1"]}) == fmt_address({**tail, "adresse": ["c/o Example", "Street 1"]})


def test_positive_new_claim_is_reported_despite_other_source_failure():
    claim = {"id": "one", "family": "jobs", "field": "job", "value": "Engineer", "evidence_ids": ["e"]}
    previous = {"claims": [], "evidence": []}
    current = {"claims": [claim], "evidence": [{"id": "e"}], "availability": {"jobs": {"state": "blocked"}}}
    changes, _ = diff(previous, current, detected_at=AT)
    assert [c["type"] for c in changes] == ["new_job"]


def test_nav_ad_not_carried_forward_without_active_revalidation():
    claim = {"id": "one", "family": "jobs", "field": "job_posting", "value": {"title": "Engineer"}, "evidence_ids": ["e"]}
    old = {"claims": [claim], "evidence": [{"id": "e", "source_url": "https://pam-stilling-feed.nav.no/ad/one"}]}
    current = {"claims": [], "evidence": [], "availability": {"jobs": {"state": "blocked"}}}
    changes, _ = diff(old, current, detected_at=AT)
    assert not changes and not current["claims"]


def test_ambiguous_refresh_does_not_report_false_removal():
    claim = {"id": "one", "family": "leadership", "field": "ceo", "value": "Person", "evidence_ids": ["e"]}
    old = {"claims": [claim], "evidence": [{"id": "e"}]}
    current = {"claims": [], "evidence": [], "availability": {"leadership": {"state": "ambiguous"}}}
    changes, meta = diff(old, current, detected_at=AT)
    assert not changes and "leadership" in meta["not_compared"]
    assert current["claims"][0]["stale_since"] == AT


def test_currency_change_is_material_even_when_value_matches():
    claim = {"id": "one", "family": "financials", "field": "revenue", "value": 100, "unit": "NOK", "evidence_ids": ["e"]}
    old = {"claims": [claim], "evidence": [{"id": "e"}]}
    current = {"claims": [dict(claim, id="two", unit="EUR")], "evidence": [{"id": "e"}], "availability": {"financials": {"state": "available"}}}
    changes, _ = diff(old, current, detected_at=AT)
    assert len(changes) == 1 and changes[0]["previous_unit"] == "NOK" and changes[0]["current_unit"] == "EUR"


@pytest.mark.parametrize("value", ["today", "2026-11-09T00:00:00"])
def test_cutoff_requires_unambiguous_timestamp(value):
    with pytest.raises(ValueError):
        instant(value)


def test_watchdog_never_exits_successfully_on_write_failure(tmp_path, monkeypatch):
    r = runner(tmp_path)
    r.budget.max_seconds = 0
    monkeypatch.setattr(r, "write", lambda *_: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr("signalpost.pipeline.os._exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))
    try:
        with pytest.raises(SystemExit) as exc:
            r._hard_watchdog()
        assert exc.value.code == 1
    finally:
        r.fetcher.close()

@pytest.mark.parametrize("published, accepted", [("2026-11-09T01:00:00Z", False), ("2026-11-09T01:00:00+02:00", True)])
def test_cutoff_compares_full_claim_timestamp(tmp_path, published, accepted):
    from signalpost.model import Claim
    r = runner(tmp_path, evidence_cutoff=AT)
    snap = source({"title": "Fixture article"})
    try:
        r.store.capture(snap)
        pb = r.builders[ORG]
        ev = pb.add_evidence(Evidence(snap.url, "official_registry", AT, snap.sha256, '"title": "Fixture article"', "fixture"))
        pb.add(Claim("activity", "company_news", {"title": "Fixture article"}, [ev], effective_date=published))
        env = r.envelope(ORG, AT, None)
        assert any(c.get("field") == "company_news" for c in env["claims"]) is accepted
    finally:
        r.fetcher.close()
