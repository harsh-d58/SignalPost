"""Candidate-attribution probe. Observations never become independent labels.

python eval/website_modes.py PILOT --out OUTPUT
Reads candidates.jsonl, refreshes legal identity, and visits at most two candidates
per company through the production URL/robots gates. No search API or paid source.
"""
import argparse
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

from build_website_corpus import candidate_url
from signalpost.budget import Budget, BudgetExhausted
from signalpost.http import Fetcher
from signalpost.registry import fetch_entities
from signalpost.web import visit_site, find_orgnrs, NON_COMPANY_HOSTS


def probe(pilot, out, max_requests=1000, max_seconds=600, workers=4):
    if out.exists(): raise FileExistsError('Use a fresh probe directory')
    rows=[json.loads(l) for l in (pilot/'candidates.jsonl').read_text(encoding='utf-8').splitlines()]
    out.mkdir(parents=True)
    budget=Budget(max_requests=max_requests,max_seconds=max_seconds,safety_requests=25,safety_seconds=45)
    fetcher=Fetcher(budget)
    started=time.monotonic()
    anchors, errors=fetch_entities(fetcher,[r['organisation_number'] for r in rows])
    def one(row):
        org=row['organisation_number']; observations=[]
        if org not in anchors:
            return {**row,'anchor_state':'unavailable','observations':[], 'ownership_judgment':None}
        entity, snap=anchors[org]
        candidates=[]
        for raw, origin in [(entity.get('hjemmeside'),'registry_declared'),(row.get('candidate_url'),'universe_snapshot')]:
            url=candidate_url(raw)
            if url and url not in [u for u,_ in candidates]: candidates.append((url,origin))
        for url, origin in candidates[:2]:
            host=urlsplit(url).hostname.lower()
            if any(host == h or host.endswith('.'+h) for h in NON_COMPANY_HOSTS):
                observations.append({'candidate_url':url,'discovery_source':origin,'observed_decision':'skipped_platform','gate_reason':'not an eligible company-site route'})
                continue
            try:
                visit=visit_site(fetcher,url,origin,org,entity,entity.get('navn',''),set(),max_subpages=2)
                observations.append({'candidate_url':url,'discovery_source':origin,'observed_decision':visit.decision,'gate_reason':visit.reason,
                    'proof_url':visit.proof_page.url if visit.proof_page else None,'proof_span':visit.proof_span,
                    'pages':[{'url':p.url,'retrieved_at':p.snap.retrieved_at,'content_sha256':p.snap.sha256,
                              'title':p.title,'observed_org_numbers':sorted(find_orgnrs(p.text))} for p in visit.pages]})
            except BudgetExhausted:
                observations.append({'candidate_url':url,'discovery_source':origin,'observed_decision':'not_attempted_budget'})
                break
            except Exception as exc:
                observations.append({'candidate_url':url,'discovery_source':origin,'observed_decision':'failed','error_type':type(exc).__name__})
        return {**row,'legal_name':entity.get('navn'),'anchor_state':'available',
                'anchor':{'source_url':snap.url,'retrieved_at':snap.retrieved_at,'content_sha256':snap.sha256},
                'observations':observations,'ownership_judgment':None,'reviewer':''}
    try:
        results=[]
        with (out/'observations.jsonl').open('x',encoding='utf-8') as handle, ThreadPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(one,rows):
                results.append(result);handle.write(json.dumps(result,ensure_ascii=False)+'\n');handle.flush()
                if len(results)%20==0: print(f"[probe] {len(results)}/{len(rows)} companies; requests={budget.requests}",flush=True)
        tasks=[]
        for row in results:
            org=row['organisation_number'];name=row.get('legal_name') or row.get('name_at_universe_snapshot') or ''
            tasks.append({'organisation_number':org,'cohort':row['cohort'],'legal_name':name,
                          'candidate_urls':[o['candidate_url'] for o in row['observations']],
                          'search_queries':[f'"{org}"',f'"{name}" "{row.get("municipality_at_universe_snapshot") or ""}"',f'"{name}" (kontakt OR "om oss")'],
                          'ownership_judgment':None,'reviewer':'','evidence_url':'','reference_facts':[],
                          'note':'Review independently. Query suggestions were not executed. Candidate/gate results are not labels.'})
        (out/'review-tasks.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in tasks),encoding='utf-8')
        report={'mode':'candidate_attribution_probe','companies':len(results),'input_sha256':hashlib.sha256((pilot/'candidates.jsonl').read_bytes()).hexdigest(),
                'requests':budget.requests,'elapsed_seconds':round(time.monotonic()-started,1),'external_cost_usd':0,
                'candidate_outcomes':dict(Counter(o['observed_decision'] for r in results for o in r['observations'])),
                'companies_with_accepted_candidate':sum(any(o['observed_decision']=='accepted' for o in r['observations']) for r in results),
                'companies_without_candidate':sum(not r['observations'] for r in results),'registry_errors':errors,
                'independently_labeled':0,'precision':None,'recall':None,
                'limitation':'Production gate observations on an injected-candidate development cohort. Not discovery recall, verified labels or a blind evaluation.'}
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        return report
    finally: fetcher.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pilot',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--max-requests',type=int,default=1000);parser.add_argument('--max-seconds',type=int,default=600)
    args=parser.parse_args()
    print(json.dumps(probe(args.pilot,args.out,args.max_requests,args.max_seconds),indent=2))
