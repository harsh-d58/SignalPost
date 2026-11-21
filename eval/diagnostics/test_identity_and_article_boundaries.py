"""Regressions for ownership and article classification failures at 6a87ab7."""
import hashlib

import pytest

from signalpost.http import Snapshot
from signalpost.model import ProfileBuilder
from signalpost.web import Page, article_page, extract_company_owned, visit_site


def snapshot(url, body, status=200):
    raw = body.encode()
    return Snapshot(url, url, status, "2026-11-19T12:00:00Z", body=raw,
                    content_type="text/html", sha256=hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("title,expect_website", [
    ("OTIS AS", True),
    ("Otis Worldwide", False),
    ("West OTIS AS", False),
    ("Customer story: OTIS AS", False),
    ("OTIS AS | Otis India", False),
])
def test_publication_from_registry_candidate(monkeypatch, title, expect_website):
    url = "https://www.otis.com/"
    body = (f"<title>{title}</title><p>Independent elevator installation and engineering "
            "services throughout the region. Contact our team for a quote and further "
            "information about our projects and capabilities.</p>")
    class Fetch:
        def get(self, target, **kwargs):
            return snapshot(target, body) if target == url else snapshot(target, "", 404)

    monkeypatch.setattr("signalpost.web.host_is_public", lambda _: True)
    fetch = Fetch()
    profile = ProfileBuilder("919419105")
    visit = visit_site(fetch, url, "registry_declared", profile.org,
                       {"epostadresse": "service@otis.com"}, "OTIS AS", set())
    extract_company_owned(profile, fetch, visit, "OTIS AS", defer_enrichment=True)
    assert bool(profile.family_claims("website")) == expect_website


def test_real_prose_length_independent_of_layout():
    url = "https://example.no/news/story"
    paragraph = "<p>Contact our sales desk today for a print catalogue.</p>"
    assert not article_page(Page(snapshot(url, f"<main><article>{paragraph}</article></main>")))


def test_customer_named_in_page_metadata_cannot_own_group_site():
    from eval.diagnostics.audit_core_rules import publisher_probe
    assert publisher_probe()["published_customer_host"] is False


@pytest.mark.parametrize("markup", [
    '<title>OTIS AS</title><meta property="og:site_name" content="Parent Group AS">',
    '<title>OTIS AS</title><script type="application/ld+json">{"@type":"Organization","legalName":"Parent AS"}</script>',
    '<title>Parent AS</title><meta property="og:title" content="OTIS AS">',
])
def test_conflicting_operator_metadata(markup):
    assert not Page(snapshot("https://group.example.no/", markup)).identity_quote("OTIS AS")
