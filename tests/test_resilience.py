import copy
import json
import threading

import httpx
import pytest

from signalpost.budget import Budget, BudgetExhausted
from signalpost.http import Fetcher, Snapshot
from signalpost.jobs import BASE, JobFeed, job_claims
from signalpost.model import ProfileBuilder
from signalpost.registry import accounts_claims, fetch_activity, fetch_entities, subunit_claims
from signalpost.refresh import diff
from signalpost.synthesis import build_brief, money
from test_publication import ORG, OTHER, NAME, TODAY, Fetch, page, snap, visit
from signalpost.web import _news, _site_jobs, normalize_site


def json_snap(value, url="https://registry.no/data", status=200):
    return snap(json.dumps(value), url, status=status)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("signalpost.http.host_is_public", lambda h: h not in {"localhost", "private.no"})
    f = Fetcher(Budget(max_requests=100, safety_requests=0, safety_seconds=0))
    f.client.close()
    yield f
    f.close()


@pytest.mark.parametrize("location", ["http://127.0.0.1/", "http://private.no/", "http://user:pass@example.no/", "http://example.no:1234/", "file:///secret", "http://[bad", "http://example.no:bad"])
def test_api_redirect_obeys_url_policy(client, location):
    seen = []
    def respond(req):
        seen.append(str(req.url))
        return httpx.Response(302, headers={"location": location})
    client.client = httpx.Client(transport=httpx.MockTransport(respond))
    assert not client.get_json("https://example.no/start", phase="test", retries=0).ok
    assert len(seen) == 1


def test_cross_origin_redirect_strips_token(client):
    headers = []
    def respond(req):
        headers.append(req.headers.get("authorization"))
        return httpx.Response(302, headers={"location": "https://other.no/end"}) if len(headers) == 1 else httpx.Response(200, json={})
    client.client = httpx.Client(transport=httpx.MockTransport(respond))
    assert client.get_json("https://example.no/start", phase="test", headers={"Authorization": "Bearer test"}).ok
    assert headers == ["Bearer test", None]


def test_redirect_destination_robots_is_checked(client):
    seen = []
    def respond(req):
        seen.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /" if req.url.host == "other.no" else "User-agent: *\nAllow: /")
        return httpx.Response(302, headers={"location": "https://other.no/private"})
    client.client = httpx.Client(transport=httpx.MockTransport(respond))
    result = client.get("https://example.no/", phase="test")
    assert result.error == "blocked_robots"
    assert "https://other.no/private" not in seen
    assert client.budget.requests == 3


@pytest.mark.parametrize("status,allowed", [(404, True), (410, True), (403, False), (500, False), (429, False)])
def test_robots_outcomes(client, status, allowed):
    client.client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(status)))
    assert client.allowed_by_robots("https://example.no/", "test") is allowed


def test_truncated_body_is_never_success(client):
    client.client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, text="x" * 100)))
    result = client.get("https://example.no/", phase="test", api=True, max_bytes=10)
    assert not result.ok and result.error == "body_too_large"


@pytest.mark.parametrize("bad", ["not JSON", "[]", '{"_embedded":{"enheter":12}}'])
def test_registry_malformed_batch_is_contained(bad):
    class F:
        def get_json(self, *args, **kw):
            return snap(bad)
    rows, errors = fetch_entities(F(), [ORG])
    assert not rows and errors
    assert fetch_activity(F(), [ORG])[2]


@pytest.mark.parametrize("value", [None, True, False, "100", float("nan"), float("inf"), {}, []])
def test_invalid_financial_values_never_published(value):
    pb = ProfileBuilder(ORG)
    accounts_claims(pb, json_snap([{"regnskapsperiode": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
                                  "eiendeler": {"sumEiendeler": value}}]))
    assert not pb.family_claims("financials")


@pytest.mark.parametrize("value", [0, -125, 100.5])
def test_real_zero_negative_and_decimal_preserved(value):
    pb = ProfileBuilder(ORG)
    accounts_claims(pb, json_snap([{"eiendeler": {"sumEiendeler": value}}]))
    assert pb.family_claims("financials")[0].value == value


def test_wrong_company_accounts_and_workplaces_rejected():
    pb = ProfileBuilder(ORG)
    accounts_claims(pb, json_snap([{"organisasjonsnummer": OTHER, "eiendeler": {"sumEiendeler": 100}}]))
    subunit_claims(pb, json_snap({"_embedded": {"underenheter": [{"organisasjonsnummer": "999999999", "overordnetEnhet": OTHER}]}}))
    assert not pb.claims


def test_real_news_and_distinct_same_title_jobs():
    pb = ProfileBuilder(ORG)
    pb.extra["legal_name"] = NAME
    nodes = [{"@type": "NewsArticle", "headline": "Our new factory opens", "datePublished": TODAY, "url": "/news/factory"}]
    nodes += [{"@type": "JobPosting", "title": "Marine engineer", "datePosted": TODAY, "directApply": True,
               "hiringOrganization": {"name": NAME, "identifier": ORG}, "url": "/jobs/" + location} for location in ("oslo", "bergen")]
    v = visit(page(nodes=[nodes[0]], url="https://fjord.no/news/factory"))
    v.pages.extend(page(nodes=[node], url="https://fjord.no" + node["url"]) for node in nodes[1:])
    _news(pb, Fetch(), v, v.origin)
    _site_jobs(pb, v)
    assert len(pb.family_claims("activity")) == 1
    assert len(pb.family_claims("jobs")) == 2
    assert all(c.value["url"].startswith("https://") for c in pb.claims.values())


def test_partial_refresh_retains_unseen_but_reports_new_job():
    old = {"id": "old", "family": "jobs", "field": "job_posting", "key": "old", "value": {"title": "Old"}, "evidence_ids": ["e"]}
    prev = {"claims": [old], "evidence": [{"id": "e"}], "run": {"completed_at": "yesterday"}}
    new = dict(old, id="new", key="new", value={"title": "New"})
    cur = {"claims": [new], "evidence": [{"id": "e"}], "availability": {"jobs": {"state": "available"}}, "incomplete_families": {"jobs": "partial"}}
    changes, meta = diff(prev, cur, detected_at=TODAY)
    assert [c["type"] for c in changes] == ["new_job"]
    assert "jobs" in meta["not_compared"]
    assert next(c for c in cur["claims"] if c["id"] == "old")["stale_since"] == TODAY
    assert "Old" not in str(build_brief(cur))


def test_unknown_currency_is_not_invented():
    assert "NOK" not in money(100, None)


@pytest.mark.parametrize("url", ["javascript://example.no", "file://example.no", "https://example.no:bad", "https://[bad"])
def test_bad_website_candidate_is_ignored(url):
    assert normalize_site(url) is None


def test_company_path_is_preserved():
    assert normalize_site("https://group.no/companies/fjord") == "https://group.no/companies/fjord"


def test_concurrent_requests_cannot_overdraw_budget():
    budget = Budget(max_requests=10, safety_requests=0, safety_seconds=0)
    def spend():
        try:
            budget.acquire("example.no", "test")
        except BudgetExhausted:
            pass
    threads = [threading.Thread(target=spend) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert budget.requests == 10


@pytest.mark.parametrize("employer,status,expires,expected", [
    (ORG, "ACTIVE", "2099-01-01", True),
    (OTHER, "ACTIVE", "2099-01-01", False),
    (ORG, "INACTIVE", "2099-01-01", False),
    (ORG, "ACTIVE", "2020-01-01", False),
    (ORG, "ACTIVE", "garbage", False),
])
def test_nav_publication_gate(employer, status, expires, expected):
    class F:
        def get_json(self, *args, **kw):
            return json_snap({"status": status, "ad_content": {"employer": {"orgnr": employer, "name": NAME},
                             "title": "Engineer", "published": TODAY, "expires": expires,
                             "link": "https://parent.no/careers"}})
    feed = JobFeed(F())
    feed.done.set()
    feed.ads = {"ad1": {"uuid": "ad1", "status": "ACTIVE", "business_name": NAME, "url": BASE + "/ad1"}}
    pb = ProfileBuilder(ORG)
    job_claims(pb, feed, [NAME], {ORG})
    assert bool(pb.family_claims("jobs")) is expected
    if expected:
        assert pb.family_claims("jobs")[0].value["url"] == "https://arbeidsplassen.nav.no/stillinger/stilling/ad1"


def test_partial_nav_feed_does_not_report_absence():
    feed = JobFeed(Fetch())
    feed.error = "feed HTTP 500"
    feed.ads = {"unrelated": {"status": "ACTIVE", "business_name": "Other AS"}}
    feed.done.set()
    pb = ProfileBuilder(ORG)
    job_claims(pb, feed, [NAME], {ORG})
    assert pb.families["jobs"].state == "failed"


def test_nav_latest_inactive_entry_wins(monkeypatch):
    monkeypatch.setenv("NAV_FEED_TOKEN", "test")
    class F:
        def get_json(self, *args, **kw):
            return json_snap({"items": [
                {"_feed_entry": {"uuid": "x", "status": status, "sistEndret": date}, "url": "/ads/x"}
                for status, date in [("INACTIVE", "2026-11-07T10:00:00Z"), ("ACTIVE", "2026-11-06T10:00:00Z")]]})
    feed = JobFeed(F())
    feed._run()
    assert feed.ads["x"]["status"] == "INACTIVE"
    assert feed.complete and feed.done.is_set()


@pytest.mark.parametrize("deadline, observed, closed", [
    ("2020-01-01", TODAY, True),
    ("2026-11-11T02:00:00+02:00", "2026-11-10T23:59:59Z", False),
    ("2026-11-11T02:00:00+02:00", "2026-11-11T00:00:00Z", True),
    ("2026-11-11T02:00:00+02:00", "2026-11-11T00:00:01Z", True),
])
def test_expired_job_is_closed_even_with_partial_feed(deadline, observed, closed):
    old = {"id": "old", "family": "jobs", "field": "job_posting", "key": "old", "value": {"title": "Old", "expires": deadline}, "evidence_ids": ["e"]}
    prev = {"claims": [old], "evidence": [{"id": "e"}]}
    cur = {"claims": [], "evidence": [], "availability": {"jobs": {"state": "failed"}}, "incomplete_families": {"jobs": "partial"}}
    changes, _ = diff(prev, cur, detected_at=observed)
    assert [c["type"] for c in changes] == (["closed_job"] if closed else [])
    assert bool(cur["claims"]) is not closed


def test_evidence_words_alone_do_not_validate_an_excerpt():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("verify_evidence", Path(__file__).resolve().parents[1] / "eval/verify_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not module.span_present('Company revenue: 100; Other company profit: 5', '"revenue": 5')
    assert module.span_present('{"revenue":100}', '"revenue": 100')
    assert module.span_present('{"organisasjonsform":{"kode":"AS","_links":{},"beskrivelse":"Aksjeselskap"}}',
                               '"organisasjonsform": {"beskrivelse": "Aksjeselskap", "kode": "AS"}')
    article = """<script type="application/ld+json">
        {"headline":"Office opens","datePublished":"2026-11-11","publisher":{"name":"Fjord","contactPoint":"omitted"}}
        </script>"""
    proof = '{"headline":"Office opens","datePublished":"2026-11-11","publisher":{"name":"Fjord"}}'
    assert module.span_present(article, proof)
    assert not module.span_present(article, proof.replace("2026-11-11", "2026-11-12"))
    assert module.span_present(
        "<html><head><meta property='article:published_time' content='2026-11-11'/></head></html>",
        '<meta property="article:published_time" content="2026-11-11">',
    )


@pytest.mark.parametrize("response_headers, second_headers, requests", [
    ({"Cache-Control": "public, max-age=300"}, {}, 1),
    ({"Cache-Control": "public, max-age=300, no-store"}, {}, 2),
    ({"Cache-Control": "public, max-age=300", "Age": "300"}, {}, 2),
    ({"Cache-Control": "public, max-age=300", "Vary": "*"}, {}, 2),
    ({"Cache-Control": "public, max-age=300"}, {"Accept-Language": "en"}, 2),
    ({"Cache-Control": "public, max-age=300"}, {"Authorization": "Bearer fixture"}, 2),
])
def test_response_reuse_obeys_freshness_and_request_context(monkeypatch, response_headers, second_headers, requests):
    from signalpost import http

    monkeypatch.setattr(http, "check_url", lambda url: http.urllib.parse.urlsplit(url))
    fetcher = http.Fetcher(Budget())
    fetcher.client.close()
    fetcher.client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, text="public source", headers=response_headers)))
    try:
        first = fetcher.get("https://fixture.no/source", phase="web", api=True)
        second = fetcher.get("https://fixture.no/source", phase="web", api=True, headers=second_headers)
        assert first.ok and second.ok
        assert fetcher.budget.requests == requests
    finally:
        fetcher.close()


@pytest.mark.parametrize("content_type,body", [
    ('text/html; CHARSET="windows-1252"', 'Rørlegger Øst'.encode('cp1252')),
    ('text/html', '<meta charset="windows-1252">Rørlegger Øst'.encode('cp1252')),
    ('text/html', 'Rørlegger Øst'.encode('utf-8')),
    ('text/html', 'Rørlegger Øst'.encode('cp1252')),
])
def test_norwegian_encoding_is_preserved(content_type, body):
    value = Snapshot('https://x.no', 'https://x.no', 200, TODAY, body=body, content_type=content_type).text()
    assert 'Rørlegger Øst' in value and '\ufffd' not in value


@pytest.mark.parametrize("width", [1, 2, 7, 10000])
def test_bulk_json_handles_arbitrary_chunks_and_key_order(width):
    import io
    from signalpost.bulk import _json_array
    rows = [{"rollegrupper": [], "_links": {"self": {"href": "source"}}}, {"navn": "Rørlegger", "n": 2}]
    class Chunks(io.StringIO):
        def read(self, size=-1):
            return super().read(min(width, size) if size >= 0 else width)
    assert list(_json_array(Chunks(json.dumps(rows)))) == rows


@pytest.mark.parametrize("body", ['[{"a":1}', '[{"a":1} {"b":2}]', '{}', '', '[1]'])
def test_bulk_malformed_json_fails_instead_of_claiming_absence(body):
    import io
    from signalpost.bulk import _json_array
    with pytest.raises(ValueError):
        list(_json_array(io.StringIO(body)))

@pytest.mark.parametrize("cacheable", [True, False])
def test_concurrent_requests_share_only_cacheable_responses(monkeypatch, cacheable):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from signalpost import http

    monkeypatch.setattr(http, "check_url", lambda url: http.urllib.parse.urlsplit(url))
    started, release = threading.Event(), threading.Event()
    calls = []
    def respond(request):
        calls.append(request)
        started.set()
        assert release.wait(3)
        return httpx.Response(200, text="public", headers={"Cache-Control": "public, max-age=300" if cacheable else "no-store"})
    fetcher = http.Fetcher(Budget())
    fetcher.client.close()
    fetcher.client = httpx.Client(transport=httpx.MockTransport(respond))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(fetcher.get, "https://fixture.no/source", phase="web", api=True)
            assert started.wait(3)
            second = pool.submit(fetcher.get, "https://fixture.no/source", phase="web", api=True)
            release.set()
            assert first.result().ok and second.result().ok
        assert len(calls) == (1 if cacheable else 2)
        assert not fetcher._inflight
    finally:
        release.set()
        fetcher.close()


def test_dns_failures_expire_instead_of_poisoning_process(monkeypatch):
    from signalpost import http
    clock = [100.0]
    answers = [False, True]
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    http._dns_cache.clear()
    def resolve(*args, **kwargs):
        if not answers.pop(0):
            raise OSError("temporary DNS failure")
        return [(None, None, None, None, ("8.8.8.8", 0))]
    monkeypatch.setattr(http.socket, "getaddrinfo", resolve)
    try:
        assert not http.host_is_public("fixture.no")
        assert not http.host_is_public("fixture.no")
        clock[0] += 6
        assert http.host_is_public("fixture.no")
    finally:
        http._dns_cache.clear()


def test_inflight_failure_releases_waiters(monkeypatch):
    from signalpost import http
    fetcher = http.Fetcher(Budget())
    calls = []
    def fail_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("fixture failure")
        return Snapshot("https://fixture.no", "https://fixture.no", 200, TODAY, body=b"ok")
    monkeypatch.setattr(fetcher, "_cached_get", fail_once)
    try:
        with pytest.raises(RuntimeError):
            fetcher.get("https://fixture.no", phase="web")
        assert not fetcher._inflight
        assert fetcher.get("https://fixture.no", phase="web").ok
        assert not fetcher._inflight
    finally:
        fetcher.close()


def test_inflight_wait_obeys_deadline_without_removing_owner(monkeypatch):
    import threading
    from signalpost import http
    fetcher = http.Fetcher(Budget())
    url = "https://fixture.no"
    key = (url, False, http.MAX_BODY_BYTES, None, ())
    owner = threading.Event()
    fetcher._inflight[key] = owner
    monkeypatch.setattr(fetcher.budget, "time_left", lambda: 0)
    try:
        with pytest.raises(BudgetExhausted, match="waiting"):
            fetcher.get(url, phase="web")
        assert fetcher._inflight[key] is owner
        assert not owner.is_set()
    finally:
        fetcher.close()
