"""Unresolved acceptance probes. Run explicitly; failures document pending work."""
import pytest

from signalpost.model import ProfileBuilder
from signalpost.refresh import diff
from signalpost.web import Page, _news, _site_jobs
from test_improvement_cases import BASE, DATE, NAME, ORG, OTHER, Pages, offline_clock, page, snapshot, verified


@pytest.mark.parametrize("case", ["foreign-publisher-html", "sibling-host", "future-time"])
def test_remaining_news_publication_boundaries(case):
    home = page(body='<a href="/news/opening">News</a>')
    node = {"@type": "NewsArticle", "headline": "New office opens in Bergen", "datePublished": DATE}
    body = ""
    if case == "foreign-publisher-html":
        node["publisher"] = {"identifier": OTHER}
        body = f'<meta property="article:published_time" content="{DATE}"><h1>New office opens in Bergen</h1>'
    if case == "future-time":
        node["datePublished"] = "2026-11-11T23:00:00Z"
    article = page("/news/opening", nodes=[node], body=body)
    if case == "sibling-host":
        url = "https://parent.example.no/news/opening"
        home = page(body=f'<a href="{url}">News</a>')
        article = Page(snapshot(article.snap.text(), url))
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(article.snap), verified(home), BASE + "/")
    assert not pb.family_claims("activity"), case


@pytest.mark.parametrize("closed", [False, True], ids=["missing-ad-control", "explicitly-closed-ad"])
def test_remaining_refresh_distinguishes_closed_from_unobserved(closed):
    node = {"@type": "JobPosting", "title": "Marine engineer", "datePosted": DATE,
            "validThrough": "2026-12-01", "hiringOrganization": {"identifier": ORG}}
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, verified(page("/jobs/engineer", nodes=[node])))
    previous = {"claims": [c.to_dict() for c in pb.family_claims("jobs")],
                "evidence": [e.to_dict() for e in pb.evidence.values()]}
    current_pb = ProfileBuilder(ORG)
    current_pb.extra["legal_name"] = NAME
    detail = page("/jobs/engineer", nodes=[node], body="Applications closed.") if closed else page()
    _site_jobs(current_pb, verified(detail))
    current = {"claims": [], "evidence": [e.to_dict() for e in current_pb.evidence.values()], "availability": {"jobs": {"state": "not_available"}},
               "incomplete_families": current_pb.extra["incomplete_families"],
               "closed_jobs": current_pb.extra.get("closed_jobs", {})}
    changes, _ = diff(previous, current, detected_at="2026-11-11T00:00:00Z")
    if closed:
        assert not current["claims"], "explicit closure must supersede the old future deadline"
        assert any(c["type"] == "closed_job" for c in changes)
    else:
        assert len(current["claims"]) == 1
        assert current["claims"][0]["stale_since"]
        assert not changes

@pytest.mark.parametrize("publisher, url, expected", [
    ({"identifier": OTHER}, None, False),
    ({"identifier": ORG}, None, True),
    ({"identifier": OTHER}, BASE + "/news/another-story", True),
])
def test_article_publisher_conflict_applies_to_html_time(publisher, url, expected):
    node = {"@type": "NewsArticle", "headline": "Different article", "publisher": publisher}
    if url:
        node["url"] = url
    detail = page("/news/opening", nodes=[node], body=f'<article><h1>New office opens</h1><time itemprop="datePublished" datetime="{DATE}"></time></article>')
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(), verified(detail), BASE + "/")
    assert bool(pb.family_claims("activity")) is expected


@pytest.mark.parametrize("date, expected", [
    ("2026-11-11T00:00:00Z", True),
    ("2026-11-11T00:00:01Z", False),
    ("2026-11-11T01:00:00+02:00", True),
    ("2026-11-10T23:00:00-02:00", False),
    ("2026-11-10T12:00:00", False),
    ("2026-11-10", True),
])
def test_article_publication_instant(date, expected):
    detail = page("/news/opening", nodes=[{"@type": "NewsArticle", "headline": "New office opens", "datePublished": date}])
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(), verified(detail), BASE + "/")
    assert bool(pb.family_claims("activity")) is expected
    if expected and "T" in date:
        assert "T" in pb.family_claims("activity")[0].effective_date


def test_job_sidebar_closure_does_not_close_current_ad():
    node = {"@type": "JobPosting", "title": "Marine engineer", "datePosted": DATE,
            "validThrough": "2026-12-01", "hiringOrganization": {"identifier": ORG}}
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, verified(page("/jobs/engineer", nodes=[node], body='<main><h1>Marine engineer</h1><aside>Applications closed.</aside></main>')))
    assert len(pb.family_claims("jobs")) == 1
    assert not pb.extra.get("closed_jobs")


def test_sitemap_after_dead_news_link():
    home = page(body='<a href="/news">News</a><a href="/sitemap.xml">Sitemap</a>')
    article = page("/news/opening", nodes=[{"@type": "NewsArticle", "headline": "New office opens", "datePublished": DATE}])
    sitemap = snapshot(f'<urlset><url><loc>{article.url}</loc></url></urlset>', BASE + '/sitemap.xml')
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(sitemap, article.snap), verified(home), BASE + "/")
    assert len(pb.family_claims("activity")) == 1


def test_explicit_job_closure_is_evidenced_and_idempotent():
    import copy
    node = {"@type": "JobPosting", "title": "Marine engineer", "datePosted": DATE,
            "validThrough": "2026-12-01", "hiringOrganization": {"identifier": ORG}}
    active = ProfileBuilder(ORG)
    active.extra["legal_name"] = NAME
    _site_jobs(active, verified(page("/jobs/engineer", nodes=[node])))
    previous = {"claims": [c.to_dict() for c in active.family_claims("jobs")],
                "evidence": [e.to_dict() for e in active.evidence.values()]}
    closed = ProfileBuilder(ORG)
    closed.extra["legal_name"] = NAME
    _site_jobs(closed, verified(page("/jobs/engineer", nodes=[node], body='<main>' + '<p>Background information.</p>' * 100 + '<p>Applications closed.</p></main>')))
    current = {"claims": [], "evidence": [e.to_dict() for e in closed.evidence.values()],
               "availability": {"jobs": {"state": "not_available"}},
               "closed_jobs": closed.extra["closed_jobs"], "incomplete_families": closed.extra["incomplete_families"]}
    repeated = copy.deepcopy(current)
    changes, _ = diff(previous, current, detected_at="2026-11-11T00:00:00Z")
    assert len(changes) == 1 and changes[0]["type"] == "closed_job"
    assert len(changes[0]["evidence_ids"]) == 2
    assert not current["claims"]
    assert diff(current, repeated, detected_at="2026-11-12T00:00:00Z")[0] == []
    reopened = copy.deepcopy(previous)
    reopened["availability"] = {"jobs": {"state": "available"}}
    assert diff(current, reopened, detected_at="2026-11-12T00:00:00Z")[0][0]["type"] == "new_job"


def test_robots_declared_sitemap_is_discovery_only():
    home = page()
    article = page("/news/opening", nodes=[{"@type": "NewsArticle", "headline": "New office opens", "datePublished": DATE}])
    sitemap = snapshot(f'<urlset><url><loc>{article.url}</loc><lastmod>2099-01-01</lastmod></url></urlset>', BASE + '/sitemap.xml')
    fetcher = Pages(sitemap, article.snap)
    fetcher.sitemap_urls = lambda _: [BASE + '/sitemap.xml']
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, fetcher, verified(home), BASE + "/")
    assert pb.family_claims("activity")[0].effective_date == DATE


@pytest.mark.parametrize("status,error,expect_http", [(403, None, False), (404, None, False), (0, "ConnectTimeout", True), (0, "blocked_robots", False)])
def test_https_fallback_is_limited_to_transport_errors(status, error, expect_http):
    from signalpost.web import visit_site
    snap = snapshot("", BASE + "/", status=status)
    snap.error = error
    fetcher = Pages(snap)
    visit_site(fetcher, BASE + "/", "registry_declared", ORG, {}, NAME, set())
    assert any(u.startswith("http://") for u in fetcher.calls) is expect_http


def test_deferred_enrichment_does_not_fetch_details_during_verification():
    from signalpost.web import extract_company_owned, enrich_company_owned
    home = page(body='<a href="/jobs/engineer">Jobs</a><a href="/news/opening">News</a>')
    fetcher = Pages()
    pb = ProfileBuilder(ORG)
    visit = verified(home)
    extract_company_owned(pb, fetcher, visit, NAME, defer_enrichment=True)
    assert pb.family_claims("website")
    assert not fetcher.calls
    assert pb.extra["deferred_site"] is visit
    enrich_company_owned(pb, fetcher, visit)
    assert BASE + '/jobs/engineer' in fetcher.calls
    assert BASE + '/news/opening' in fetcher.calls

@pytest.mark.parametrize("owner,duplicate,expected", [(ORG, False, True), (OTHER, False, False), (ORG, True, False)])
def test_publisher_graph_resolution_keeps_exact_identity(owner, duplicate, expected):
    from signalpost.web import _resolved_publisher
    definition = {"@type": "Organization", "@id": BASE + "/#organization", "name": NAME, "identifier": owner}
    article = {"@type": "Article", "headline": "New office opens", "datePublished": DATE,
               "publisher": {"@id": BASE + "/#organization"}}
    nodes = [definition, article] + ([{**definition, "identifier": OTHER}] if duplicate else [])
    p = page("/news/opening", nodes=nodes, body=f'<meta property="article:published_time" content="{DATE}"><h1>New office opens</h1>')
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    _news(pb, Pages(), verified(p), BASE + "/")
    assert bool(pb.family_claims("activity")) is expected
    if expected:
        from pathlib import Path
        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_graph", Path(__file__).resolve().parents[1] / "verify_evidence.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        for ev in pb.evidence.values():
            assert verifier.span_present(p.raw, ev.claim_span)
