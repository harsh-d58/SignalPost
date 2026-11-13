"""Compare candidate-injected gate observations with an org-only baseline.

This is a stage diagnosis, not precision/recall. Labels are intentionally absent.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def compare(probe, run, output):
    observed=[json.loads(l) for l in (probe/'observations.jsonl').read_text(encoding='utf-8').splitlines()]
    baseline=list(map(json.loads,(run/'envelopes.jsonl').read_text(encoding='utf-8').splitlines()))
    envs={e['organisation_number']:e for e in baseline}
    orgs=[r['organisation_number'] for r in observed]
    if len(set(orgs))!=len(orgs) or len(envs)!=len(baseline) or set(orgs)!=set(envs):
        raise ValueError('Probe and baseline must contain the same unique company set')
    rows=[]
    for row in observed:
        env=envs[row['organisation_number']]
        accepted=any(o['observed_decision']=='accepted' for o in row['observations'])
        websites=[c['value'] for c in env['claims'] if c['field']=='official_website' and c.get('availability','available')=='available' and not c.get('stale_since')]
        state=env['availability']['website']
        if websites: stage='baseline_published_website'
        elif accepted and 'budget' in state.get('reason','').lower(): stage='probe_accepts_baseline_budget_limited'
        elif accepted: stage='probe_accepts_baseline_missing_review_required'
        elif not row['observations']: stage='no_candidate_or_anchor'
        elif any(o['observed_decision']=='not_attempted_budget' for o in row['observations']): stage='probe_budget_limited'
        else: stage='candidate_gate_unresolved_or_rejected'
        rows.append({'organisation_number':row['organisation_number'],'cohort':row['cohort'],'stage':stage,
                     'probe_has_accepted_candidate':accepted,'baseline_websites':websites,'baseline_state':state,
                     'independent_ownership_label':None})
    report={'companies':len(rows),'mode':'stage_diagnosis','stages':dict(Counter(r['stage'] for r in rows)),
            'cohorts':{c:dict(Counter(r['stage'] for r in rows if r['cohort']==c)) for c in sorted({r['cohort'] for r in rows})},
            'precision':None,'recall':None,'rows':rows,
            'limitation':'Injected candidates and production gate outputs are not reference labels. Differences may also reflect observation time and source availability.'}
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('probe',type=Path);p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();r=compare(args.probe,args.run,args.output)
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
