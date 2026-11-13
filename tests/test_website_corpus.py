import gzip
import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('website_corpus',Path(__file__).resolve().parents[1]/'eval/build_website_corpus.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def fixture_rows():
    rows=[]
    def add(name,url):
        rows.append({'organisation_number':str(900000000+len(rows)),'name':name,'website':url})
    for i in range(160): add(f'Operating Business {i} AS',f'https://unique{i}.example.no')
    for i in range(40):
        for n in range(2): add(f'Shared Company {i} {n} AS',f'https://shared{i}.example.no')
    for i in range(40): add(f'Company {i} HOLDING AS',f'https://holding{i}.example.no')
    for i in range(40): add(f'Scoped Company {i} AS',f'https://scope{i}.example.no/company')
    return rows


def test_pilot_selection_is_disjoint_deterministic_and_unlabeled():
    rows=fixture_rows();excluded={r['organisation_number'] for r in rows[:5]}
    a=m.select(rows,excluded,20261112);b=m.select(list(reversed(rows)),excluded,20261112)
    assert a==b and len(a)==100
    assert len({r['organisation_number'] for r in a})==100
    assert not {r['organisation_number'] for r in a}&excluded
    assert all(r['ownership_judgment'] is None and not r['reference_facts'] for r in a)
    assert sum(r['cohort']=='positive_candidate' for r in a)==40
    assert sum(r['cohort']=='random' for r in a)==20


@pytest.mark.parametrize('url', ['ftp://example.no','https://user:secret@example.no','https://example.no:9999','https://'])
def test_candidate_url_rejects_unsafe_shapes(url):
    assert m.candidate_url(url) is None


def test_bad_corpus_digest_never_creates_output(tmp_path):
    source=tmp_path/'input.gz'
    with gzip.open(source,'wb') as f:f.write(b'{"organisation_number":"123"}\n')
    with pytest.raises(ValueError,match='hash'):
        m.build(source,tmp_path/'out',[],1)
    assert not (tmp_path/'out').exists()


def test_existing_pilot_cannot_overwrite_labels(tmp_path):
    target=tmp_path/'out';target.mkdir();(target/'labels.jsonl').write_text('reviewed')
    with pytest.raises(FileExistsError):m.build(tmp_path/'missing.gz',target,[],1)
    assert (target/'labels.jsonl').read_text()=='reviewed'


def test_stage_comparison_does_not_call_probe_acceptance_recall(tmp_path):
    spec=importlib.util.spec_from_file_location('website_metrics',Path(__file__).resolve().parents[1]/'eval/website_metrics.py')
    metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
    observed={'organisation_number':'123','cohort':'positive_candidate','observations':[{'observed_decision':'accepted'}]}
    env={'organisation_number':'123','claims':[],'availability':{'website':{'state':'failed','reason':'request budget exhausted'}}}
    (tmp_path/'observations.jsonl').write_text(json.dumps(observed))
    (tmp_path/'envelopes.jsonl').write_text(json.dumps(env))
    r=metrics.compare(tmp_path,tmp_path,tmp_path/'diagnosis.json')
    assert r['precision'] is None and r['recall'] is None
    assert r['stages']=={'probe_accepts_baseline_budget_limited':1}
    env['organisation_number']='456'
    (tmp_path/'envelopes.jsonl').write_text(json.dumps(env))
    with pytest.raises(ValueError,match='same unique'):
        metrics.compare(tmp_path,tmp_path,tmp_path/'other.json')

    env['organisation_number']='123'
    (tmp_path/'envelopes.jsonl').write_text(json.dumps(env)+'\n'+json.dumps(env))
    with pytest.raises(ValueError,match='same unique'):
        metrics.compare(tmp_path,tmp_path,tmp_path/'duplicate.json')
