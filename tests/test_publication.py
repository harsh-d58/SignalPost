"""Adversarial publication fixtures: every accepted item must identify the exact company."""
import hashlib
import json
from datetime import datetime, timezone

import pytest

from signalpost.http import Snapshot
from signalpost.model import ProfileBuilder
from signalpost.web import Page, SiteVisit, _news, _parse_date, _site_jobs, _social_ok, visit_site

ORG = "923609016"
OTHER = "984661185"
NAME = "Fjord Marine Service AS"
TODAY = datetime.now(timezone.utc).date().isoformat()


def snap(html, url="https://fjord.no/", final=None, status=200):
    body = html.encode()
    return Snapshot(url, final or url, status, TODAY + "T00:00:00Z", body=body,
                    content_type="text/html", sha256=hashlib.sha256(body).hexdigest())


def page(body="", nodes=None, url="https://fjord.no/"):
    if "/news/" in url:
        body += '<main><p>Our new service office opened in Bergen today. The team will support local marine customers with repairs, installation and scheduled maintenance from next week.</p></main>'
    script = '<script type="application/ld+json">' + json.dumps(nodes or []) + '</script>'
    return Page(snap('<html><title>' + NAME + '</title>' + script + '<body>' + body + '</body></html>', url))


class Fetch:
    def __init__(self, pages=None):
        self.pages = pages or {}
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(url)
        return self.pages.get(url, snap("", url, status=404))


def visit(p):
    v = SiteVisit(p.url, "registry_declared")
    v.pages = [p]
    v.proof_page = p
    v.decision = "accepted"
    return v


@pytest.mark.parametrize("handle", ["fjordgroup", "fjordmarineserviceagency", "fjordmarine", "wordpress", "fjordmarineservicesister"])
def test_social_sameas_is_not_identity_proof(handle):
    url = "https://linkedin.com/company/" + handle
    assert not _social_ok("linkedin", url, page(), NAME, "fjord.no", {url})


@pytest.mark.parametrize("handle", ["fjord-marine-service", "fjordmarineservice", "fjordmarineserviceas", "fjord_marine_service"])
def test_social_full_company_handle(handle):
    assert _social_ok("linkedin", "https://linkedin.com/company/" + handle, page(), NAME, "fjord.no", set())


def test_identity_name_cannot_be_assembled_from_unrelated_fields():
    p = page()
    p.title = "Fjord"
    p.meta = {"og:site_name": "Marine", "og:title": "Service"}
    assert not p.identity_quote(NAME)


def test_identity_proof_quotes_legal_name_instead_of_short_brand_title():
    p = page(nodes=[{"@type": "Organization", "name": "Fjord", "legalName": NAME}])
    p.title = "Fjord"
    assert p.identity_quote(NAME) == NAME


@pytest.mark.parametrize("date", ["2026-02-30", "2026-13-01", "2026-10-03garbage", 123, {}, []])
def test_invalid_publication_date(date):
    assert _parse_date(date) is None


def test_multiple_footer_companies_do_not_establish_ownership(monkeypatch):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    p = page(f'<p>{"Company information " * 15}</p><footer>Org.nr {ORG}; Org.nr {OTHER}</footer>')
    v = visit_site(Fetch({p.url: p.snap}), p.url, "registry_declared", ORG, {}, NAME, {OTHER})
    assert v.decision != "accepted"


def test_contact_redirect_cannot_prove_original_site(monkeypatch):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    p = page('<p>' + 'Welcome to the group. ' * 15 + '</p><a href="/contact">Contact</a>')
    p.title = "Parent Group"
    home = snap('<html><title>Parent Group</title><body>' + 'Welcome. ' * 30 + '<a href="/contact">Contact</a></body></html>')
    contact = snap(f'<footer>Org.nr {ORG}</footer>', 'https://fjord.no/contact', 'https://different.no/')
    v = visit_site(Fetch({p.url: home, 'https://fjord.no/contact': contact}), p.url, "registry_declared", ORG, {}, NAME, set())
    assert v.decision != "accepted"


def test_repeated_brand_in_group_title_cannot_prove_subsidiary(monkeypatch):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    home = snap('<html><title>Welcome to the Kappahl Group / Kappahl</title><body>' + 'Global fashion brand. ' * 20 + '</body></html>')
    v = visit_site(Fetch({home.url: home}), home.url, "registry_declared", ORG,
                   {"epostadresse": "post@fjord.no"}, "KAPPAHL AS", set())
    assert v.decision != "accepted"


@pytest.mark.parametrize("node", [
    {"@type": "Event", "name": "New product launch", "startDate": TODAY, "url": "/events/launch"},
    {"@type": "NewsArticle", "headline": "See more news", "datePublished": TODAY, "url": "/news"},
    {"@type": "NewsArticle", "headline": "A new product", "dateModified": TODAY, "url": "/news/new-product"},
    {"@type": "NewsArticle", "headline": "Another firm's story", "datePublished": TODAY, "url": "https://other.no/news/story"},
])
def test_non_news_is_not_published(node):
    pb = ProfileBuilder(ORG)
    v = visit(page(nodes=[node]))
    _news(pb, Fetch(), v, v.origin)
    assert not pb.family_claims("activity")


def test_atom_updated_is_not_a_publish_date():
    p = page()
    p.feeds = ["https://fjord.no/feed"]
    feed = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>New factory opens</title><link href="https://fjord.no/news/factory"/><updated>' + TODAY + '</updated></entry></feed>'
    pb = ProfileBuilder(ORG)
    _news(pb, Fetch({p.feeds[0]: snap(feed, p.feeds[0])}), visit(p), "https://fjord.no/")
    assert not pb.family_claims("activity")


def test_news_deduplicates_encoded_and_literal_article_urls():
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    nodes = [
        {"@type": "NewsArticle", "headline": "New office opens in Tromsø", "datePublished": TODAY, "url": url}
        for url in ("/news/tromsø", "/news/troms%c3%b8")
    ]
    v = visit(page(nodes=nodes, url="https://fjord.no/news/tromsø"))
    _news(pb, Fetch(), v, v.origin)
    assert [c.value["url"] for c in pb.family_claims("activity")] == ["https://fjord.no/news/troms%C3%B8"]


@pytest.mark.parametrize("employer,url", [
    ({"name": "Fjord Group AS", "identifier": OTHER}, "/jobs/engineer"),
    ({"name": NAME}, "/careers"),
    ({"name": NAME}, "https://arbeidsplassen.nav.no/stillinger"),
    ({}, "/jobs/engineer"),
])
def test_jobs_need_exact_employer_and_single_ad(employer, url):
    pb = ProfileBuilder(ORG)
    p = page(nodes=[{"@type": "JobPosting", "title": "Marine engineer", "datePosted": TODAY,
                     "hiringOrganization": employer, "url": url}])
    pb.extra["legal_name"] = NAME
    _site_jobs(pb, visit(p))
    assert not pb.family_claims("jobs")


@pytest.mark.parametrize("body,name,expected", [
    (f'<title>{NAME}</title><footer>Org.nr {ORG}</footer>', NAME, True),
    (f'<title>Parent Group</title><footer>Org.nr {OTHER}</footer>', NAME, False),
    (f'<title>Parent Group</title><main>Our customer {NAME}, org.nr {ORG}</main>', NAME, False),
    (f'<title>{NAME}</title><footer>Org.nr {ORG}, Org.nr {OTHER}</footer>', NAME, False),
])
def test_website_ownership_positive_and_negative(monkeypatch, body, name, expected):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    home = snap('<html><body>' + body + '</body></html>')
    v = visit_site(Fetch({home.url: home}), home.url, "registry_declared", ORG, {}, name, set())
    assert (v.decision == "accepted") is expected


def test_nested_article_and_job_schema_are_discovered():
    p = page(nodes={"@type": "WebPage", "mainEntity": {"@type": "NewsArticle", "headline": "Factory opens", "datePublished": TODAY}})
    assert any(n.get("@type") == "NewsArticle" for n in p.jsonld)


def test_embedded_employer_is_not_site_owner(monkeypatch):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    html = '<html><title>Vacancies Board</title><script type="application/ld+json">' + json.dumps(
        {"@type": "JobPosting", "title": "Engineer", "hiringOrganization": {"@type": "Organization", "name": NAME, "identifier": ORG}}) + '</script><body>' + 'Jobs for many companies. ' * 20 + '</body></html>'
    home = snap(html)
    v = visit_site(Fetch({home.url: home}), home.url, "registry_declared", ORG, {}, NAME, set())
    assert v.decision != "accepted"


def test_unlabelled_or_modified_html_time_is_not_news():
    pb = ProfileBuilder(ORG)
    p = page('<article><h2><a href="/news/factory">Our new factory opens</a></h2><time class="updated" datetime="' + TODAY + '">Updated</time></article>')
    _news(pb, Fetch(), visit(p), p.url)
    assert not pb.family_claims("activity")


def test_published_html_article_is_news():
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    p = page('<article><h2><a href="/news/factory">Our new factory opens</a></h2><time itemprop="datePublished" datetime="' + TODAY + '">Published</time></article>', url="https://fjord.no/news/factory")
    _news(pb, Fetch(), visit(p), p.url)
    assert len(pb.family_claims("activity")) == 1


def test_news_listing_requires_reachable_dated_detail():
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    listing = page(nodes=[{"@type": "NewsArticle", "headline": "Our new factory opens", "datePublished": TODAY, "url": "/news/factory"}])
    _news(pb, Fetch(), visit(listing), listing.url)
    assert not pb.family_claims("activity")
    detail = page(nodes=[{"@type": "NewsArticle", "headline": "Our new factory opens", "datePublished": TODAY}], url="https://fjord.no/news/factory")
    _news(pb, Fetch({detail.url: detail.snap}), visit(listing), listing.url)
    assert len(pb.family_claims("activity")) == 1
    assert next(iter(pb.evidence.values())).source_url == detail.url


def test_job_listing_payload_is_discovery_only():
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    node = {"@type": "JobPosting", "title": "Marine engineer", "datePosted": TODAY, "directApply": True,
            "hiringOrganization": {"name": NAME, "identifier": ORG}, "url": "/jobs/engineer"}
    _site_jobs(pb, visit(page(nodes=[node], url="https://fjord.no/careers")))
    assert not pb.family_claims("jobs")
    _site_jobs(pb, visit(page(nodes=[node], url="https://fjord.no/jobs/engineer")))
    assert len(pb.family_claims("jobs")) == 1


def test_feed_product_is_not_news_but_article_is_verified():
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    p = page()
    p.feeds = ['https://fjord.no/feed']
    feed = '<rss><channel><item><title>Our new factory opens</title><link>https://fjord.no/news/factory</link><pubDate>' + TODAY + '</pubDate></item></channel></rss>'
    article = page(nodes=[{"@type": "NewsArticle", "headline": "Our new factory opens", "datePublished": TODAY}], url='https://fjord.no/news/factory')
    f = Fetch({p.feeds[0]: snap(feed, p.feeds[0]), article.url: article.snap})
    _news(pb, f, visit(p), p.url)
    assert len(pb.family_claims("activity")) == 1 and article.url in f.calls


def test_third_party_publisher_on_company_site_is_not_own_news():
    pb = ProfileBuilder(ORG)
    pb.extra['legal_name'] = NAME
    p = page(nodes=[{"@type": "NewsArticle", "headline": "New factory opens", "datePublished": TODAY,
                     "url": "/news/factory", "publisher": {"name": "Parent Group AS"}}])
    _news(pb, Fetch(), visit(p), p.url)
    assert not pb.family_claims("activity")
