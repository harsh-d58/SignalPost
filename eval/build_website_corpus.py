"""Freeze a fresh 100-company website research pilot. Candidate strata are not labels."""
import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED = 'b82d6a3e7231d1759a958c282bc4366b80ec2fab8095053d8ed7fa9cd01bc838'


def candidate_url(value):
    value = (value or '').strip()
    if not value:
        return None
    value = value if '://' in value else 'https://' + value
    try:
        p = urlsplit(value)
        if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password or p.port not in (None, 80, 443):
            return None
        return value
    except ValueError:
        return None


def excluded_orgs(paths):
    result = set()
    for path in paths:
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt', encoding='utf-8-sig') as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if isinstance(row, dict):
                    org = row.get('organisation_number') or row.get('organisasjonsnummer')
                    if org:
                        result.add(str(org))
    return result


def select(rows, excluded, seed):
    hosts = Counter(urlsplit(u).hostname.lower() for r in rows if (u := candidate_url(r.get('website'))))
    available = [r for r in rows if r['organisation_number'] not in excluded]
    available.sort(key=lambda r: hashlib.sha256(f"{seed}:{r['organisation_number']}".encode()).digest())
    chosen, used, challenge_hosts = [], set(), set()
    def take(count, cohort, predicate, distinct_host=False):
        found = 0
        for row in available:
            org = row['organisation_number']
            url = candidate_url(row.get('website'))
            host = urlsplit(url).hostname.lower() if url else None
            if org in used or not predicate(row, url, host) or (distinct_host and host in challenge_hosts):
                continue
            item = {'organisation_number': org, 'name_at_universe_snapshot': row.get('name'),
                    'municipality_at_universe_snapshot': row.get('municipality'),
                    'industry_code_at_universe_snapshot': row.get('industry_code'),
                    'cohort': cohort, 'candidate_url': url, 'candidate_source': 'universe_website' if url else None,
                    'known_exact_host_entity_count': hosts[host] if host else 0,
                    'split': 'development_pilot', 'ownership_judgment': None, 'reviewer': '', 'reference_facts': []}
            chosen.append(item); used.add(org)
            if distinct_host: challenge_hosts.add(host)
            found += 1
            if found == count: break
        if found != count: raise ValueError(f'Insufficient candidates for {cohort}: {found}/{count}')
    take(20, 'random', lambda r,u,h: True)
    take(20, 'challenge_shared_host', lambda r,u,h: bool(u and hosts[h] > 1), True)
    take(10, 'challenge_holding_name', lambda r,u,h: bool(u and any(t in r.get('name','').upper().split() for t in ('HOLDING','INVEST','EIENDOM'))), True)
    take(10, 'challenge_scoped_path', lambda r,u,h: bool(u and urlsplit(u).path.strip('/')), True)
    take(40, 'positive_candidate', lambda r,u,h: bool(u and hosts[h] == 1 and not any(t in r.get('name','').upper().split() for t in ('HOLDING','INVEST','EIENDOM'))), True)
    return chosen


def build(universe, out, exclusions, seed):
    if out.exists(): raise FileExistsError('Use a fresh output directory; existing labels must not be overwritten')
    rows=[]; digest=hashlib.sha256()
    with gzip.open(universe,'rb') as handle:
        for raw in handle:
            digest.update(raw); rows.append(json.loads(raw))
    if digest.hexdigest() != EXPECTED: raise ValueError('Universe content hash mismatch')
    excluded=excluded_orgs(exclusions)
    selected=select(rows, excluded, seed)
    out.mkdir(parents=True)
    for filename, content in [('companies.jsonl', [{'organisation_number':r['organisation_number']} for r in selected]), ('candidates.jsonl', selected)]:
        (out/filename).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in content),encoding='utf-8')
    manifest={'seed':seed,'universe_sha256':digest.hexdigest(),'universe_rows':len(rows),'excluded_entities':len(excluded),
              'exclusion_files':[str(p) for p in exclusions], 'entities':len(selected),'strata':dict(Counter(r['cohort'] for r in selected)),
              'candidate_urls':sum(bool(r['candidate_url']) for r in selected),'independently_reviewed':0,
              'companies_sha256':hashlib.sha256((out/'companies.jsonl').read_bytes()).hexdigest(),
              'limitations':'Candidate-enriched development pilot. Positive labels are not established; shared-host, holding and path strata are research hints. Not a blinded or representative pooled benchmark.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('universe',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--exclude',type=Path,nargs='*',default=[]);parser.add_argument('--seed',type=int,default=20261112)
    args=parser.parse_args()
    print(json.dumps(build(args.universe,args.out,args.exclude,args.seed),indent=2))
