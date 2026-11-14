"""Export a minimal licensed-registry dataset for the JBOX read-only demo."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = {'legal_name', 'legal_form', 'municipality', 'industry_code', 'industry_label', 'employees',
          'founded_date', 'registered_date', 'bankrupt', 'liquidating', 'revenue', 'sales_revenue',
          'net_result', 'operating_result', 'total_assets', 'equity', 'total_debt', 'cash'}
CLAIM_KEYS = {'id','family','field','label','value','unit','period','note','effective_date','evidence_ids'}
EVIDENCE_KEYS = {'id','source_url','source_class','retrieved_at','content_sha256','claim_span','extraction_method','license'}


def profile(row):
    org = row['organisation_number']
    if not re.fullmatch(r'\d{9}', org):
        raise ValueError('Invalid organisation number')
    evidence = {}
    for e in row.get('evidence', []):
        url = urlsplit(e.get('source_url', ''))
        if (e.get('source_class') == 'official_registry' and e.get('license') == 'NLOD-2.0'
                and url.scheme == 'https' and url.hostname == 'data.brreg.no' and not url.username
                and e.get('retrieved_at') and e.get('claim_span')
                and re.fullmatch(r'[a-f0-9]{64}', e.get('content_sha256',''))
                and e.get('locator', {}).get('organisation_number') == org):
            evidence[e['id']] = {k:v for k,v in e.items() if k in EVIDENCE_KEYS}
    claims = [{k:v for k,v in c.items() if k in CLAIM_KEYS} for c in row.get('claims', [])
              if c.get('field') in FIELDS and c.get('value') is not None
              and c.get('availability','available') == 'available' and not c.get('stale_since')
              and c.get('evidence_ids') and all(i in evidence for i in c['evidence_ids'])]
    refs = {i for c in claims for i in c['evidence_ids']}
    first = lambda f: next((c['value'] for c in claims if c['field'] == f), None)
    return {'organisation_number':org, 'name':first('legal_name'),
            'observed_at':row.get('run',{}).get('completed_at'),
            'availability': {f:{'state':'available' if any(c['family']==f for c in claims) else 'not_available',
                                'reason':'Limited licensed-registry demo export; omitted fields are not absence claims.'}
                             for f in ['identity','status','industry','financials']},
            'claims':claims,'evidence':[evidence[i] for i in sorted(refs)]}


def export(source, out):
    if out.exists(): raise FileExistsError('Use a fresh output directory')
    rows = [json.loads(l) for l in source.read_text(encoding='utf-8-sig').splitlines() if l.strip()]
    profiles = [profile(r) for r in rows]
    if len({r['organisation_number'] for r in profiles}) != len(profiles): raise ValueError('Duplicate organisation number')
    if any(not p['name'] for p in profiles): raise ValueError('Every demo company needs supported legal identity')
    (out/'companies').mkdir(parents=True)
    index = []
    for p in profiles:
        (out/'companies'/f"{p['organisation_number']}.json").write_text(json.dumps(p,ensure_ascii=False)+'\n',encoding='utf-8')
        first = lambda f: next((c['value'] for c in p['claims'] if c['field']==f), None)
        index.append({'organisation_number':p['organisation_number'],'name':p['name'],
                      'municipality':first('municipality'),'legal_form':first('legal_form')})
    result = {'schema_version':'signalpost-jbox/1','company_count':len(index),
              'observed_at':max((p['observed_at'] or '' for p in profiles),default=''),
              'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'limitations':'Dated development sample, not all Norwegian companies. Only selected NLOD-2.0 registry facts; external sites, contacts, roles and raw snapshots excluded. Source consistency is not independent accuracy.',
              'companies':index}
    (out/'index.json').write_text(json.dumps(result,ensure_ascii=False)+'\n',encoding='utf-8')
    return {'companies':len(profiles),'claims':sum(len(p['claims']) for p in profiles),'evidence':sum(len(p['evidence']) for p in profiles)}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(export(args.source,args.out)))
