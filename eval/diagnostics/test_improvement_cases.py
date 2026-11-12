"""Offline acceptance probes for the improvement programme, outside default CI.

These tests express desired behaviour. Known failures stay red until implemented;
they are not regressions in the existing 164-test suite and are never xfailed.
Run explicitly: python -m pytest eval/diagnostics -q -p no:cacheprovider
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from signalpost.budget import Budget
from signalpost.console.server import build_cmd
from signalpost.evidence import SnapshotStore
from signalpost.http import Fetcher, Snapshot
from signalpost.jobs import JobFeed
from signalpost.model import ProfileBuilder
from signalpost.synthesis import build_brief
from signalpost.web import Page, SiteVisit, _news, _site_jobs, visit_site

ORG = "923609016"
OTHER = "984661185"
NAME = "Fjord Marine Service AS"
DATE = "2026-11-10"
STAMP = "2026-11-11T00:00:00Z"
BASE = "https://fjord.example.no"


@pytest.fixture(autouse=True)
def offline_clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 11, 11, tzinfo=timezone.utc)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    def no_network(*args, **kwargs):
        raise AssertionError("diagnostic fixtures must not access the network")

    monkeypatch.setattr("signalpost.web.datetime", Clock)
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    monkeypatch.setattr("signalpost.http.host_is_public", lambda _: True)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)


def snapshot(body, url, status=200, content_type="text/html"):
    raw = body.encode()
    return Snapshot(url, url, status, STAMP, body=raw, content_type=content_type,
                    sha256=hashlib.sha256(raw).hexdigest())


def page(path="/", nodes=None, body="", title=NAME):
    markup = f'<html><head><title>{title}</title><script type="application/ld+json">'
    markup += json.dumps(nodes or []) + f"</script></head><body>{body}</body></html>"
    return Page(snapshot(markup, BASE + path))


def verified(p):
    visit = SiteVisit(p.url, "registry_declared")
    visit.pages = [p]
    visit.proof_page = p
    visit.decision = "accepted"
    return visit


class Pages:
    def __init__(self, *pages):
        self.pages = {p.url: p for p in pages}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.pages.get(url, snapshot("", url, status=404))


@pytest.mark.parametrize("contact_title, accepted", [(NAME, True), ("Fjord Marine Service ASA", False)])
def test_D01_contact_page_name_and_registry_phone_prove_entity(contact_title, accepted):
    home = page(body='Marine equipment and engineering services. ' * 8 + '<a href="/contact">Contact</a>', title="Fjord")
    contact = page("/contact", body="Company contact telephone 22 33 44 55", title=contact_title)
    result = visit_site(Pages(home.snap, contact.snap), home.url, "registry_declared", ORG,
                        {"telefon": "22334455"}, NAME, set())
    assert (result.decision == "accepted") is accepted, f"{result.decision}; {result.reason}"
    if accepted:
        assert result.proof_page.url == contact.url


def test_D02_news_retained_source_proves_publication_date(tmp_path):
    p = page("/news/new-office", nodes=[{"@type": "NewsArticle", "headline": "New office opens in Bergen",
             "datePublished": DATE, "publisher": {"name": NAME, "identifier": ORG}}])
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(), verified(p), BASE + "/")
    assert len(pb.family_claims("activity")) == 1, "fixture must first produce a real article claim"
    store = SnapshotStore(tmp_path)
    store.capture(p.snap)
    fragments = []
    for evidence in pb.evidence.values():
        record = store.bind(evidence.to_dict())
        assert record
        fragments.append((tmp_path / record["object"]["path"]).read_text(encoding="utf-8"))
    assert any(DATE in text and "datePublished" in text for text in fragments), "retained source contains title but no publication-date fragment"


def test_D03_job_retained_source_proves_employer_and_dates(tmp_path):
    p = page("/jobs/engineer", nodes=[{"@type": "JobPosting", "title": "Marine engineer", "datePosted": DATE,
             "validThrough": "2026-12-10", "hiringOrganization": {"name": NAME, "identifier": ORG}}])
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, verified(p))
    assert len(pb.family_claims("jobs")) == 1, "fixture must first produce a job claim"
    store = SnapshotStore(tmp_path)
    store.capture(p.snap)
    fragments = []
    for evidence in pb.evidence.values():
        record = store.bind(evidence.to_dict())
        assert record
        fragments.append((tmp_path / record["object"]["path"]).read_text(encoding="utf-8"))
    source = " ".join(fragments)
    assert all(value in source for value in (ORG, "hiringOrganization", DATE, "datePosted", "validThrough")), "retained job title does not prove employer or dates"


def test_D04_equivalent_reference_fact_matches_different_internal_key(tmp_path):
    spec = importlib.util.spec_from_file_location("diagnostic_metrics", Path(__file__).parents[1] / "metrics.py")
    metrics = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metrics)
    claim = {"family": "website", "field": "official_website", "key": "official_website", "value": BASE + "/"}
    env = {"organisation_number": ORG, "claims": [claim], "availability": {"website": {"state": "available"}}}
    (tmp_path / "envelopes.jsonl").write_text(json.dumps(env) + "\n", encoding="utf-8")
    (tmp_path / "run-report.json").write_text(json.dumps({"run_id": "fixture", "agent_version": "fixture", "input_count": 1,
        "validation": {"passed": True}, "operations": {"requests": 0, "elapsed_seconds": 0}, "third_party_cost_usd": 0}), encoding="utf-8")
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps({**claim, "organisation_number": ORG, "key": "reviewer-website-1"}) + "\n", encoding="utf-8")
    result = metrics.measure(tmp_path, pool)
    assert result["local_pool"]["families"]["website"]["matched_claims"] == 1, "identical company, field and URL missed because reviewer key differs"


def test_D05_registry_event_does_not_hide_unknown_company_news():
    claim = {"id": "fixture", "family": "activity", "field": "registry_event", "value": {"title": "Registry update"},
             "effective_date": DATE, "evidence_ids": ["fixture-evidence"]}
    brief = build_brief({"claims": [claim], "availability": {"activity": {"state": "available", "reason": "registry events"}}})
    assert any(u.get("field") == "company_news" for u in brief["unknowns"]), "available registry activity hides missing company news"


def test_D06_reusable_response_avoids_duplicate_outbound_requests():
    fetcher = Fetcher(Budget())
    fetcher.client.close()
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, text="same public resource", headers={"Cache-Control": "public, max-age=300"})

    fetcher.client = httpx.Client(transport=httpx.MockTransport(respond))
    try:
        a = fetcher.get(BASE + "/shared", phase="web", api=True)
        b = fetcher.get(BASE + "/shared", phase="web", api=True)
        assert a.ok and b.ok
        assert len(calls) == 1, f"two identical cacheable requests caused {len(calls)} outbound requests"
        assert fetcher.budget.requests == 1
    finally:
        fetcher.close()


def test_D07_console_honors_requested_bulk_configuration():
    cmd, _ = build_cmd({"action": "run", "batch": "eval/known-15.jsonl", "out": "out-diagnostic-manual",
                        "bulk_files": True, "workers": 8, "job_days": 7})
    assert "--bulk-files" in cmd, "console silently omits requested bulk mode"
    assert "--workers" in cmd and cmd[cmd.index("--workers") + 1] == "8"


def test_D08_sitemap_discovers_article_but_detail_supplies_date():
    home = page(body='<a href="/sitemap.xml">Sitemap</a>')
    article = page("/news/new-office", nodes=[{"@type": "NewsArticle", "headline": "New office opens in Bergen", "datePublished": DATE}])
    sitemap = snapshot('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + article.url +
                       '</loc><lastmod>2026-11-11</lastmod></url></urlset>', BASE + "/sitemap.xml", content_type="application/xml")
    fetch = Pages(sitemap, article.snap)
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, fetch, verified(home), BASE + "/")
    claims = pb.family_claims("activity")
    assert len(claims) == 1, f"dated article reachable only from sitemap missed; requested={fetch.calls}"
    assert claims[0].value["date"] == DATE


def test_D09_expired_job_timestamp_is_not_active_until_end_of_day():
    # Fixture clock is 00:00 UTC. This timestamp expired two hours earlier.
    p = page("/jobs/engineer", nodes=[{"@type": "JobPosting", "title": "Engineer", "datePosted": DATE,
             "validThrough": "2026-11-11T00:00:00+02:00", "hiringOrganization": {"name": NAME, "identifier": ORG}}])
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, verified(p))
    assert not pb.family_claims("jobs"), "expired DateTime was truncated to a date and still published as active"


@pytest.mark.parametrize("foreign", [False, True], ids=["owner", "parent"])
def test_control_exact_owner_gate(foreign):
    p = page(body=f'<footer>Org.nr {OTHER if foreign else ORG}</footer>')
    result = visit_site(Pages(p.snap), p.url, "registry_declared", ORG, {}, NAME, {OTHER})
    assert (result.decision == "accepted") is not foreign


def test_control_modified_date_is_not_publication_date():
    p = page("/news/new-office", nodes=[{"@type": "NewsArticle", "headline": "New office opens in Bergen", "dateModified": DATE}])
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(), verified(p), BASE + "/")
    assert not pb.family_claims("activity")


def test_control_wrong_job_employer_is_rejected():
    p = page("/jobs/engineer", nodes=[{"@type": "JobPosting", "title": "Engineer", "datePosted": DATE,
             "hiringOrganization": {"name": "Other Company AS", "identifier": OTHER}}])
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, verified(p))
    assert not pb.family_claims("jobs")


def test_control_nav_without_credential_is_blocked_without_requests(monkeypatch):
    monkeypatch.delenv("NAV_FEED_TOKEN", raising=False)
    fetch = Pages()
    feed = JobFeed(fetch, allow_public_token=False)
    feed._run()
    assert feed.done.is_set() and not feed.complete
    assert feed.error and "NAV_FEED_TOKEN required" in feed.error
    assert fetch.calls == []
