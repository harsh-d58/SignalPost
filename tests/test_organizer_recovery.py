"""Regression cases derived from organizer feedback and the 14 November live run."""
import hashlib
import json
from datetime import datetime, timezone

import pytest

from signalpost.http import Snapshot
from signalpost.model import ProfileBuilder
from signalpost.web import Page, SiteVisit, _news, extract_company_owned, visit_site
from signalpost.refresh import diff
from signalpost.showcase.build import _index_row

ORG = "919419105"
NOW = datetime.now(timezone.utc).isoformat()


def snapshot(body, url="https://www.otis.com/", final=None):
    raw = body.encode()
    return Snapshot(url, final or url, 200, NOW, body=raw, content_type="text/html",
                    sha256=hashlib.sha256(raw).hexdigest())


class Fetch:
    def __init__(self, home):
        self.home = home
    def get(self, url, **kw):
        return self.home if url == self.home.url else Snapshot(url, url, 404, NOW)
    def sitemap_urls(self, url):
        return []


@pytest.mark.parametrize("title,accepted", [("Otis India", False), ("Otis Worldwide", False),
                                           ("Otis Group", False), ("OTIS AS", True)])
def test_regional_identity_through_publication(monkeypatch, title, accepted):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    home = snapshot(f'<html><head><title>{title}</title><meta name="description" content="Elevator manufacturing and maintenance services for regional customers and installation partners."></head><body>'
                    '<p>Elevator installation, service and manufacturing. Contact the regional office for further information about installation and scheduled maintenance services available to customers.</p></body></html>',
                    final="https://www.otis.com/en/in/" if not accepted else "https://www.otis.com/no/no/")
    fetch = Fetch(home)
    visit = visit_site(fetch, home.url, "registry_declared", ORG, {"epostadresse": "info@otis.com"}, "OTIS AS", set())
    pb = ProfileBuilder(ORG)
    extract_company_owned(pb, fetch, visit, "OTIS AS", defer_enrichment=True)
    assert bool(pb.family_claims("website")) == accepted
    if not accepted:
        assert not pb.claims
    else:
        assert pb.extra["website_identity"]["organisation_number"] == ORG
        assert pb.extra["website_identity"]["scope_path"] == "/no/no"


@pytest.mark.parametrize("state", ["ambiguous", "failed", "blocked"])
def test_refresh_ownership_revokes_but_outage_keeps_only_history(state):
    previous = {"organisation_number": ORG, "claims": [], "evidence": []}
    for family, field, value in [("website", "official_website", "https://parent.no/"),
                                  ("description", "self_description", "Parent description"),
                                  ("activity", "company_news", {"url": "https://parent.no/news/a"}),
                                  ("contact", "email", "post@parent.no")]:
        previous["claims"].append({"id": field, "key": field, "family": family, "field": field,
                                   "value": value, "evidence_ids": [field]})
        previous["evidence"].append({"id": field, "source_class": "company_owned", "source_url": "https://parent.no/"})
    current = {"organisation_number": ORG, "claims": [], "evidence": [],
               "availability": {f: {"state": state} for f in ["website", "description", "activity", "contact"]}}
    changes, _ = diff(previous, current, detected_at=NOW)
    assert _index_row(current)["w"] is None
    if state == "ambiguous":
        assert not current["claims"]
        assert len(changes) == 4
        assert all(c["type"] == "ownership_revoked" and c["previous_evidence_ids"] for c in changes)
    else:
        assert len(current["claims"]) == 4
        assert all(c.get("stale_since") for c in current["claims"])
        assert not changes


@pytest.mark.parametrize("path,title,expected", [
    ("/kontakt-oss", "Kontakt oss", False),
    ("/kontakt-oss/ledige-stillinger", "Ledige stillinger", False),
    ("/careers", "Our vacancies", False),
    ("/products/new-lift", "New lift", False),
    ("/news/new-service-office", "New service office opens", True),
])
def test_publication_metadata_requires_real_post(path, title, expected):
    body = ('Our new service office opened in Oslo today. The team will provide maintenance and installation '
            'services to local customers, with appointments available from next week.')
    node = {"@type": "Article", "headline": title, "datePublished": NOW}
    page = Page(snapshot(f'<title>OTIS AS</title><meta property="article:published_time" content="{NOW}">'
                         f'<script type="application/ld+json">{json.dumps(node)}</script>'
                         f'<article><h1>{title}</h1><p>{body}</p></article>', "https://www.otis.com" + path))
    visit = SiteVisit(page.url, "fixture")
    visit.pages = [page]
    visit.decision = "accepted"
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = "OTIS AS"
    _news(pb, Fetch(page.snap), visit, visit.origin)
    assert bool(pb.family_claims("activity")) == expected


def test_publication_timestamp_without_post_body_is_not_news():
    page = Page(snapshot(f'<title>OTIS AS</title><meta property="article:published_time" content="{NOW}">'
                         '<h1>New service office opens</h1>', "https://www.otis.com/news/new-office"))
    visit = SiteVisit(page.url, "fixture")
    visit.pages = [page]
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = "OTIS AS"
    _news(pb, Fetch(page.snap), visit, visit.origin)
    assert not pb.family_claims("activity")


@pytest.mark.parametrize('page_type', ['Product', 'JobPosting', 'ContactPage', 'AboutPage', 'CollectionPage'])
def test_cms_article_schema_does_not_override_primary_utility_type(page_type):
    from signalpost.web import article_page
    nodes = [{'@type': 'Article', 'datePublished': NOW}, {'@type': page_type}]
    raw = ('<title>OTIS AS</title><script type="application/ld+json">' + json.dumps(nodes) + '</script>'
           '<main><h1>Modern lift services</h1><p>' + 'Installation and maintenance services for regional customers. ' * 4 + '</p></main>')
    assert not article_page(Page(snapshot(raw, 'https://www.otis.com/modern-lift')))


def test_agency_footer_org_does_not_prove_customer_site(monkeypatch):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    home = snapshot('<html><title>Other Company</title><p>Information about products and services for customers.</p>'
                    f'<footer>Website by OTIS AS, org {ORG}</footer></html>')
    visit = visit_site(Fetch(home), home.url, 'registry_declared', ORG, {}, 'OTIS AS', set())
    assert visit.decision != 'accepted'


def test_invoice_identity_is_preserved_as_scoped_company_page(monkeypatch):
    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    home = snapshot('<html><title>Regional services</title><p>' + 'Corporate regional service information. ' * 8 +
                    '</p><a href="/contact">Contact</a></html>')
    contact = snapshot(f'<title>Contact</title><main>Send faktura i EHF format til OTIS AS, org {ORG}.</main>',
                       'https://www.otis.com/contact')
    class ContactFetch(Fetch):
        def get(self, url, **kw):
            return contact if url == contact.url else super().get(url, **kw)
    fetch = ContactFetch(home)
    visit = visit_site(fetch, home.url, 'registry_declared', ORG, {}, 'OTIS AS', set())
    pb = ProfileBuilder(ORG)
    extract_company_owned(pb, fetch, visit, 'OTIS AS', defer_enrichment=True)
    assert pb.family_claims('website')[0].value == contact.url
    assert pb.extra['website_identity']['scope_path'] == '/contact'


def test_client_mention_cannot_authorize_scope_inheritance():
    from signalpost.web import page_attributed
    page = Page(snapshot(f'<title>Parent company</title><main>Our customer OTIS AS, org {ORG}.</main>'))
    assert not page_attributed(page, ORG, 'OTIS AS')
