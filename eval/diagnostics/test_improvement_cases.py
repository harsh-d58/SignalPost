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
from signalpost.web import enrich_company_owned

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
    if "/news/" in path:
        body += '<main><p>Our new service office opened in Bergen today. The team will support local marine customers with repairs, installation and scheduled maintenance from next week.</p></main>'
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


@pytest.mark.parametrize("href,street,operator,accepted", [
    ("/", "Kaia 17", NAME, True), ("/customer", "Kaia 17", NAME, False),
    ("/", "Kaia 18", NAME, False), ("/", "Kaia 17", "Parent AS", False),
])
def test_registered_email_footer_operator(href, street, operator, accepted):
    body = (f'<meta property="og:site_name" content="{operator} | Our site">'
            + "<p>Marine equipment services and support.</p>" * 5
            + f'<div class="footer-info"><a href="{href}">{NAME}</a><p>{street}, 4870 Fevik</p></div>'
            + '<footer>Powered by a theme</footer>')
    home = page(body=body, title="Marine")
    entity = {"epostadresse": "post@fjord.example.no",
              "forretningsadresse": {"adresse": ["Kaia 17"], "postnummer": "4870"}}
    visit = visit_site(Pages(home.snap), home.url, "registry_email_domain", ORG, entity, NAME, set())
    assert (visit.decision == "accepted") == accepted


@pytest.mark.parametrize("title,expected", [("Engineer", True), ("Mechanic", False), ("", False)])
def test_structured_closure_at_reused_url(title, expected):
    from signalpost.refresh import diff
    ad = page("/jobs/current", nodes=[{"@type": "JobPosting", "title": title,
              "hiringOrganization": {"name": NAME}, "url": BASE + "/jobs/current"}],
              body="<main><p>Applications are closed.</p></main>")
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, verified(ad))
    key = "sitejob:" + ad.url
    old = {"id": "old", "family": "jobs", "field": "job_posting", "key": key,
           "value": {"title": "Engineer", "expires": "2026-12-01"}, "evidence_ids": []}
    current = {"claims": [], "evidence": [], "closed_jobs": pb.extra.get("closed_jobs", {}),
               "availability": {"jobs": {"state": "blocked"}}, "incomplete_families": {"jobs": "partial"}}
    changes, _ = diff({"claims": [old]}, current, detected_at=STAMP)
    assert [c["type"] for c in changes] == (["closed_job"] if expected else [])
    if expected:
        assert any("Engineer" in pb.evidence[eid].to_dict()["claim_span"] for eid in changes[0]["evidence_ids"])


@pytest.mark.parametrize("title,local_name,footer,accepted", [
    (NAME, "Fjord Marine Service", "Sandvikgata 30A, 6250 Stordal", True),
    (NAME, "Fjord Marine Service", "<div><p>Sandvikgata 30A,</p><p>6250 Stordal</p></div>", True),
    ("Our customer " + NAME, "Fjord Marine Service", "Sandvikgata 30A, 6250 Stordal", False),
    (NAME, "Parent Group", "Sandvikgata 30A, 6250 Stordal", False),
    (NAME, "Fjord Marine Service", "Sandvikgata 30B, 6250 Stordal", False),
    (NAME, "Fjord Marine Service", "Managed by Parent. Sandvikgata 30A, 6250 Stordal", False),
])
def test_homepage_business_address(title, local_name, footer, accepted):
    from signalpost.web import in_verified_scope
    entity = {"forretningsadresse": {"adresse": ["Sandvikgata 30A"], "postnummer": "6250", "poststed": "STORDAL"}}
    local = {"@type": "LocalBusiness", "name": local_name, "url": BASE,
             "address": {"addressCountry": "NO", "addressLocality": "Stordal", "postalCode": "6250"}}
    body = ('<meta property="og:site_name" content="Fjord Marine Service">'
            + '<p>Independent marine services.</p>' * 8 + f'<footer>{footer}</footer>')
    home = page(nodes=[local], body=body, title=title + " | Marine equipment")
    visit = visit_site(Pages(home.snap), home.url, "registry_declared", ORG, entity, NAME, set())
    assert (visit.decision == "accepted") == accepted
    if accepted:
        assert visit.contact_field == "business_address"
        assert in_verified_scope(home, visit, ORG, NAME)
        assert not in_verified_scope(page("/parent-jobs", nodes=[local], body=body), visit, ORG, NAME)


@pytest.mark.parametrize("label,expected", [("Publisert:", 1), ("Oppdatert:", 0)])
def test_release_detail_precedes_investor_navigation(label, expected):
    home = page(body='<a href="/investor/overview">Investor</a><a href="/borsmelding/results">Release</a>')
    release = page("/borsmelding/results", body=f'<article><h1>Quarterly results</h1><aside><h4>{label}</h4>'
                   '<div>10.11.2026</div></aside><p>' + 'The company reported increased production this quarter. ' * 3 + '</p></article>')
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    fetch = Pages(release.snap)
    _news(pb, fetch, verified(home), home.url)
    assert fetch.calls[0] == release.url
    assert len(pb.family_claims("activity")) == expected


@pytest.mark.parametrize("employer,prior,closes", [(NAME, "Engineer", True), (NAME, "Manager", False),
                                                   ("Parent Group AS", "Engineer", False)])
def test_html_early_closure_requires_same_employer_and_role(employer, prior, closes):
    from signalpost.refresh import diff
    from signalpost.web import html_vacancy
    ad = page("/jobs/engineer", body=f'<main><h1>Engineer</h1><p>Arbeidsgiver: {employer}</p>'
              '<p>Stillingen er besatt.</p></main>')
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    html_vacancy(pb, verified(ad), ad, BASE)
    old = {"id": "previous-ad", "family": "jobs", "field": "job_posting", "key": "sitejob:" + ad.url,
           "value": {"title": prior, "expires": "2026-12-01"}, "evidence_ids": []}
    current = {"claims": [], "evidence": [], "closed_jobs": pb.extra.get("closed_jobs", {}),
               "availability": {"jobs": {"state": "blocked"}}, "incomplete_families": {"jobs": "partial"}}
    changes, _ = diff({"claims": [old]}, current, detected_at=STAMP)
    assert [c["type"] for c in changes] == (["closed_job"] if closes else [])
    if closes:
        assert all(eid in pb.evidence for eid in changes[0]["evidence_ids"])


@pytest.mark.parametrize("label,operator,zip_code,accepted", [
    ("Postadresse", NAME, "1324", True), ("Kunde", NAME, "1324", False),
    ("Postadresse", "Fjord Group AS", "1324", False), ("Postadresse", NAME, "1400", False)])
def test_registry_contact_scoped_to_named_operator(label, operator, zip_code, accepted):
    from signalpost.web import in_verified_scope
    footer = f"<footer><h4>{label}</h4><p>{operator}<br>P.O Box 65<br>NO-{zip_code} Lysaker</p></footer>"
    body = '<meta property="og:site_name" content="Fjord Marine Service">' + footer + '<p>Marine services and support. </p>' * 12
    home = page(body=body, title="Marine")
    visit = visit_site(Pages(home.snap), home.url, "registry_declared", ORG,
                       {"postadresse": {"adresse": ["Postboks 65"], "postnummer": "1324"}}, NAME, set())
    assert (visit.decision == "accepted") == accepted
    if accepted:
        assert in_verified_scope(page("/job", body=body), visit, ORG, NAME)
        assert not in_verified_scope(page("/parent", body="Parent Group", title="Group"), visit, ORG, NAME)


@pytest.mark.parametrize("employer,deadline,posted,outcome", [
    (NAME, "1. desember 2026", "Publisert: 10.11.2026", "published"),
    ("Fjord Group AS", "1. desember 2026", "Publisert: 10.11.2026", "employer_unproven"),
    (NAME, "1. november 2026", "Oppstart: 1. januar 2027", "expired"),
    (NAME, "1. desember 2026", "Oppdatert: 10.11.2026", "publication_unproven"),
    (NAME, "1. desember 2026", "Publisert: 10.11.2026</p><p><strong>Søknadsfrist:</strong> 01.12.2026. Søk nå.", "published"),
    (NAME, "1. desember 2026", "Publisert: 10.11.2026</p><p>Søknadsfrist: 02.12.2026", "open_status_unproven"),
    (NAME, "1. desember 2026", "Publisert: 10.11.2026</p><p>På vegne av vår kunde", "employer_unproven"),
])
def test_visible_job_fields_on_careers_route(employer, deadline, posted, outcome):
    home = page(body='<a href="mailto:team@fjord.example.no?subject=Bestilling">Bestilling av time</a>'
                     '<a href="/jobs/engineer">Jobb</a>')
    detail = page("/jobs/engineer", body=f'<main><h1>Marine engineer</h1><p>Arbeidsgiver: {employer}</p>'
                  f'<p>{posted}</p><p>Søknadsfrist: {deadline}</p><a href="/apply/engineer">Søk her</a></main>')
    fetch = Pages(detail.snap)
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    enrich_company_owned(pb, fetch, verified(home), want_news=False)
    assert fetch.calls == [detail.url]
    assert len(pb.family_claims("jobs")) == int(outcome == "published")
    assert any(r["outcome"] == outcome for r in pb.extra["discovery_trace"])


@pytest.mark.parametrize("label,expected", [("Publisert", 1), ("Oppdatert", 0)])
def test_newsroom_card_with_unmarked_slug(label, expected):
    home = page(body='<a href="/newsroom">Newsroom</a>')
    hub = page("/newsroom", body='<main><h2><a href="/bergen-office">New Bergen office</a></h2></main>')
    detail = page("/bergen-office", body=f'<article><h1>New Bergen office</h1><span>{label}: 10.11.2026</span>'
                  '<p>Our Bergen office opens today and will serve customers along the coast with marine repairs '
                  'and scheduled maintenance.</p></article>')
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    fetch = Pages(hub.snap, detail.snap)
    _news(pb, fetch, verified(home), home.url)
    assert fetch.calls == [hub.url, detail.url]
    assert len(pb.family_claims("activity")) == expected
    assert any(row["discovery_url"] == hub.url and row["url"] == detail.url for row in pb.extra["discovery_trace"])


@pytest.mark.parametrize("employer,deadline,outcome", [
    (NAME, "2026-12-11", "published"), ("Fjord Group AS", "2026-12-11", "wrong_employer"),
    (NAME, "2026-11-01", "expired_or_invalid_deadline"),
])
def test_careers_detail_before_second_navigation_link(employer, deadline, outcome):
    home = page(body='<a href="/careers">Careers</a><a href="/jobs">Jobs</a>')
    hub = page("/careers", body='<a href="/jobs/engineer">Marine engineer</a>')
    detail = page("/jobs/engineer", nodes=[{"@type": "JobPosting", "title": "Marine engineer",
                  "datePosted": DATE, "validThrough": deadline, "hiringOrganization": {"name": employer}}])
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    fetch = Pages(hub.snap, detail.snap)
    enrich_company_owned(pb, fetch, verified(home), want_news=False)
    assert fetch.calls == [hub.url, detail.url]
    assert len(pb.family_claims("jobs")) == int(outcome == "published")
    assert any(row["url"] == detail.url and row["outcome"] == outcome for row in pb.extra["discovery_trace"])


def test_related_story_publication_date_cannot_date_main_story():
    detail = page("/news/bergen-office", body='<article><h1>New Bergen office</h1>'
                  '<section><h2>Related release</h2><span>Published: 10.11.2026</span></section></article>')
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(), verified(detail), detail.url)
    assert not pb.family_claims("activity")


@pytest.mark.parametrize("contact_title, accepted", [(NAME, True), ("Fjord Marine Service ASA", False)])
def test_D01_contact_page_name_and_registry_phone_prove_entity(contact_title, accepted):
    home = page(body='Marine equipment and engineering services. ' * 8 + '<a href="/contact">Contact</a>', title="Fjord")
    contact = page("/contact", body="Company contact telephone 22 33 44 55", title=contact_title)
    result = visit_site(Pages(home.snap, contact.snap), home.url, "registry_declared", ORG,
                        {"telefon": "22334455"}, NAME, set())
    assert (result.decision == "accepted") is accepted, f"{result.decision}; {result.reason}"
    if accepted:
        assert result.proof_page.url == contact.url
        assert result.contact_spans == ["22 33 44 55"]


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
