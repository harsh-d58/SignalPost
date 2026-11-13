"""Scheduling must improve breadth without weakening the publication gate."""
import hashlib

from signalpost.budget import BudgetExhausted
from signalpost.http import Snapshot
from signalpost.model import ProfileBuilder
from signalpost.pipeline import Runner
from signalpost.web import SiteVisit, domain_candidates, research_website, visit_site

ORGS = ['923609016', '984661185', '947942638']


def runner(tmp_path, strategy):
    r = Runner(ORGS, out_dir=tmp_path, run_id='schedule-test', bulk=None, previous=None,
               max_requests=1000, max_minutes=10, max_cost=0, workers=1, job_days=7,
               website_strategy=strategy, log=lambda *_: None)
    r.entities = {o: {'navn': 'Fjord Marine Service AS', 'hjemmeside': f'https://site{i}.no/',
                      'epostadresse': f'info@alternative{i}.no'} for i, o in enumerate(ORGS)}
    r.budget.set_phase_cap('web', 12)
    return r


def test_first_candidate_round_reaches_more_companies_under_equal_budget(tmp_path, monkeypatch):
    monkeypatch.setattr('signalpost.web.host_is_public', lambda *_: False)
    def reject(fetcher, candidate, source, org, *args, **kwargs):
        fetcher.budget.acquire('fixture.no', 'web', n=4)
        v = SiteVisit(candidate, source)
        v.decision, v.reason = 'rejected', 'different legal entity'
        return v
    monkeypatch.setattr('signalpost.web.visit_site', reject)
    broad = runner(tmp_path/'broad', 'breadth')
    legacy = runner(tmp_path/'legacy', 'legacy')
    try:
        broad.research_sites(ORGS)
        for org in ORGS:
            legacy._website_step(legacy.builders[org], org, legacy.entities[org])
        def reached(r):
            return sum(any(a['completed'] for a in pb.extra.get('website_diagnostics', {}).get('attempts', [])) for pb in r.builders.values())
        assert broad.budget.requests == legacy.budget.requests == 12
        assert reached(broad) == 3 and reached(legacy) == 2
        assert all(not pb.family_claims('website') for pb in broad.builders.values())
    finally:
        broad.fetcher.close(); legacy.fetcher.close()


def test_explicit_candidate_discovery_does_not_probe_speculative_dns(monkeypatch):
    def forbidden(*args):
        raise AssertionError('speculative DNS in explicit candidate stage')
    monkeypatch.setattr('signalpost.web.host_is_public', forbidden)
    assert domain_candidates({'navn': 'Fjord Marine Service AS', 'hjemmeside': 'fjord.no'}, None,
                             include_guesses=False) == [('https://fjord.no/', 'registry_declared')]


def test_interrupted_identity_traversal_cannot_fall_back_to_declared_name(monkeypatch):
    monkeypatch.setattr('signalpost.web.host_is_public', lambda *_: True)
    html = b'<html><title>Fjord Marine Service AS</title><body><p>We provide marine engineering, inspections, repairs and service to customers throughout Norway.</p><a href="/kontakt">Kontakt</a></body></html>'
    class Fetch:
        def get(self, url, **kwargs):
            if url.endswith('/kontakt'):
                raise BudgetExhausted('phase budget exhausted: web')
            return Snapshot(url, url, 200, '2026-11-12T00:00:00Z', body=html,
                            content_type='text/html', sha256=hashlib.sha256(html).hexdigest())
    v = visit_site(Fetch(), 'https://fjord.no/', 'registry_declared', ORGS[0],
                   {'navn': 'Fjord Marine Service AS'}, 'Fjord Marine Service AS', set())
    assert v.decision == 'budget' and v.budget_incomplete and v.proof_page is None


def test_resumed_candidates_preserve_prior_ambiguity_and_do_not_repeat(monkeypatch):
    pb = ProfileBuilder(ORGS[0]); calls = []
    cands = [('https://first.no/', 'registry_declared'), ('https://second.no/', 'registry_email_domain')]
    def visit(fetcher, candidate, source, *args, **kwargs):
        calls.append(candidate)
        v = SiteVisit(candidate, source)
        v.decision = 'ambiguous' if candidate == cands[0][0] else 'unreachable'
        v.reason = 'fixture'
        return v
    monkeypatch.setattr('signalpost.web.visit_site', visit)
    research_website(pb, None, {'navn': 'Example AS'}, None, set(), candidates=cands, max_candidates=1)
    research_website(pb, None, {'navn': 'Example AS'}, None, set(), candidates=pb.extra['website_pending_candidates'], max_candidates=1)
    assert calls == [c[0] for c in cands]
    assert pb.families['website'].state == 'ambiguous'
    assert pb.extra['website_pending_candidates'] == []


def test_budget_interrupt_keeps_candidate_for_retry(monkeypatch):
    pb = ProfileBuilder(ORGS[0]); cands = [('https://first.no/', 'registry_declared')]
    def exhausted(*args, **kwargs):
        raise BudgetExhausted('time budget exhausted')
    monkeypatch.setattr('signalpost.web.visit_site', exhausted)
    research_website(pb, None, {'navn': 'Example AS'}, None, set(), candidates=cands)
    assert pb.extra['website_pending_candidates'] == cands
    assert pb.extra['website_diagnostics']['budget_interruptions'] == 1
    assert pb.families['website'].state == 'failed'
    assert not pb.family_claims('website')


def test_budget_refusal_does_not_erase_completed_ownership_decision(tmp_path):
    r = runner(tmp_path, 'breadth')
    try:
        pb = r.builders[ORGS[0]]
        pb.set_state('website', 'ambiguous', 'conflicting legal identity')
        pb.extra['website_diagnostics'] = {'attempts': [{'completed': True, 'decision': 'ambiguous'}], 'candidate_urls': [], 'budget_interruptions': 0}
        r.budget.set_phase_cap('web', 0)
        r._website_step(pb, ORGS[0], r.entities[ORGS[0]])
        assert pb.families['website'].state == 'ambiguous'
        assert pb.families['website'].reason == 'conflicting legal identity'
    finally:
        r.fetcher.close()


def test_auto_preserves_existing_strategy_until_independent_validation(tmp_path):
    r = runner(tmp_path, 'auto')
    try:
        assert r.website_strategy == 'legacy'
    finally:
        r.fetcher.close()
