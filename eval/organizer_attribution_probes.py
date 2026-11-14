"""Offline release-blocking attribution probes; emits observed results, not reference accuracy."""
import hashlib
import json
from signalpost.http import Snapshot
from signalpost.web import Page, visit_site, _social_ok
import signalpost.web as web
from signalpost.refresh import diff
from signalpost.showcase.build import _index_row
from signalpost.model import ProfileBuilder
from datetime import datetime, timezone, timedelta


def website_probes():
    web.host_is_public=lambda _: True
    results=[]
    for title in ['Lift Manufacturing Company, Elevators & Escalators | Otis India', 'Otis Worldwide', 'OTIS AS']:
        body=f'<html><title>{title}</title><body><p>Elevators and escalators manufacturing, installation and maintenance across the world. Contact our regional teams for more information.</p></body></html>'.encode()
        class Fetch:
            def get(self,url,**kwargs):
                if url=='https://www.otis.com/':
                    return Snapshot(url,'https://www.otis.com/en/in/',200,'2026-11-14T00:00:00Z',body=body,content_type='text/html',sha256=hashlib.sha256(body).hexdigest())
                return Snapshot(url,url,404,'2026-11-14T00:00:00Z')
        v=visit_site(Fetch(),'https://www.otis.com/','registry_declared','919419105',{'navn':'OTIS AS','epostadresse':'info@otis.com'},'OTIS AS',set())
        results.append({'case':title,'observed':v.decision,'reason':v.reason,'expectation':'reject foreign regional/parent title; exact legal-name control may pass','unexpected_accept':title!='OTIS AS' and v.decision=='accepted'})
    page=Page(Snapshot('https://www.otis.com/','https://www.otis.com/',200,'2026-11-14T00:00:00Z',body=b'<title>Otis Worldwide</title>',content_type='text/html'))
    for url in ['https://www.youtube.com/user/OtisElevatorCompany','https://www.youtube.com/user/otis']:
        results.append({'case':url,'accepted':_social_ok('youtube',url,page,'OTIS AS','otis.com',{url}),'note':'Named organizer URL must fail; bare shared brand remains a risk, not an independently proven account owner.'})
    return results


def refresh_probe():
    previous = {
        'organisation_number': '888078622',
        'run': {'completed_at': '2026-11-01T00:00:00Z'},
        'claims': [{'id': 'old-manager-site', 'family': 'website',
                    'field': 'official_website', 'key': 'official_website',
                    'value': 'https://www.gbbl.no/', 'evidence_ids': ['old-proof']}],
        'evidence': [{'id': 'old-proof', 'source_url': 'https://www.gbbl.no/'}],
    }
    current = {
        'organisation_number': '888078622', 'claims': [], 'evidence': [],
        'availability': {'website': {'state': 'ambiguous',
                                    'reason': 'site presents different org number'}},
    }
    diff(previous, current, detected_at='2026-11-14T00:00:00Z')
    return {'carried': current['claims'], 'showcase_website': _index_row(current)['w'],
            'scope': 'Synthetic prior bad publication; not an assertion about a historical submitted row.'}


def news_probes():
    results = []
    stamp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    class Fetch:
        def get(self, url, **kwargs):
            return Snapshot(url, url, 404, stamp)
        def sitemap_urls(self, url):
            return []
    for path, title in [('kontakt-oss', 'Kontakt oss'),
                        ('kontakt-oss/ledige-stillinger', 'Ledige stillinger')]:
        url = 'https://example.no/' + path
        raw = (f'<html><head><title>{title}</title><meta property="og:title" content="{title}">'
               f'<meta property="article:published_time" content="{stamp}"></head>'
               f'<body><h1>{title}</h1> <p>EXAMPLE AS, org 920008259: contact details and links to vacancies.</p></body></html>').encode()
        page = Page(Snapshot(url, url, 200, stamp, body=raw, content_type='text/html',
                             sha256=hashlib.sha256(raw).hexdigest()))
        visit = web.SiteVisit(url, 'fixture')
        visit.pages = [page]
        visit.decision = 'accepted'
        pb = ProfileBuilder('920008259')
        pb.extra['legal_name'] = 'EXAMPLE AS'
        web._news(pb, Fetch(), visit, visit.origin)
        published = [c.value for c in pb.family_claims('activity') if c.field == 'company_news']
        results.append({'case': title, 'published_news': published, 'unexpected_publish': bool(published)})
    return results


def run():
    original = web.host_is_public
    try:
        return {'website_and_social': website_probes(), 'refresh': refresh_probe(), 'news': news_probes()}
    finally:
        web.host_is_public = original


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
