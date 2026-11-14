import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from signalpost.ats import greenhouse_jobs
from signalpost.http import Snapshot
from signalpost.model import ProfileBuilder
from signalpost.web import Page

BASE = 'https://boards-api.greenhouse.io/v1/boards/fjord/jobs'
NOW = datetime.now(timezone.utc)


def snap(value, url):
    raw = json.dumps(value).encode()
    return Snapshot(url, url, 200, NOW.isoformat(), body=raw, content_type='application/json',
                    sha256=hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('change,expected', [
    ({}, True),
    ({'company_name': 'Fjord Group AS'}, False),
    ({'company_name': 'Fjord Marine ASA'}, False),
    ({'first_published': None, 'updated_at': NOW.isoformat()}, False),
    ({'first_published': (NOW + timedelta(days=1)).isoformat()}, False),
    ({'application_deadline': (NOW - timedelta(days=1)).isoformat()}, False),
    ({'application_deadline': 'invalid'}, False),
])
def test_official_api_requires_exact_employer_publication_and_active_status(change, expected):
    job = {'id': 101, 'internal_job_id': 500, 'company_name': 'Fjord Marine AS', 'title': 'Marine engineer',
           'first_published': (NOW - timedelta(days=2)).isoformat(), **change}
    class Fetch:
        calls = []
        def get_json(self, url, **kwargs):
            self.calls.append(url)
            return snap({'jobs': [{'id': 101, 'internal_job_id': 500}]} if url == BASE else job, url)
    raw = b'<title>Fjord Marine AS</title><a href="https://job-boards.greenhouse.io/fjord">Careers</a>'
    page = Page(Snapshot('https://fjord.no/', 'https://fjord.no/', 200, NOW.isoformat(),
                         body=raw, content_type='text/html', sha256=hashlib.sha256(raw).hexdigest()))
    pb = ProfileBuilder('923609016')
    fetch = Fetch()
    greenhouse_jobs(pb, fetch, [page], 'Fjord Marine AS')
    assert bool(pb.family_claims('jobs')) == expected
    assert len(fetch.calls) == 2
    if expected:
        claim = pb.family_claims('jobs')[0]
        assert claim.value['url'].endswith('/fjord/jobs/101')
        assert len(claim.evidence_ids) == 2


def test_parent_page_cannot_authorize_ats_board():
    class NoFetch:
        def get_json(self, *args, **kwargs):
            pytest.fail('must not discover a board through an unproven parent page')
    page = Page(Snapshot('https://parent.no', 'https://parent.no', 200, NOW.isoformat(),
                         body=b'<title>Parent Group</title><a href="https://boards.greenhouse.io/fjord">Jobs</a>', content_type='text/html'))
    pb = ProfileBuilder('923609016')
    greenhouse_jobs(pb, NoFetch(), [page], 'Fjord Marine AS')
    assert not pb.claims
