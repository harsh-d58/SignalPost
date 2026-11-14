import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('jbox_export', Path(__file__).resolve().parents[1]/'eval/export_jbox_data.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def row():
    return {'organisation_number':'923609016','name':'SHOULD NOT BE USED','run':{'completed_at':'2026-11-12T00:00:00Z'},
            'errors':[{'secret':'private'}], 'claims':[{'id':'c','family':'identity','field':'legal_name','value':'Example AS','evidence_ids':['e']}],
            'evidence':[{'id':'e','source_class':'official_registry','license':'NLOD-2.0','source_url':'https://data.brreg.no/enhetsregisteret/api/enheter/923609016','retrieved_at':'2026-11-12T00:00:00Z','content_sha256':'a'*64,'claim_span':'Example AS','extraction_method':'json','locator':{'organisation_number':'923609016'},'snapshot_path':'private/path'}]}


def test_export_uses_supported_identity_and_drops_private_metadata():
    p=m.profile(row())
    assert p['name']=='Example AS' and len(p['claims'])==1
    assert 'errors' not in p and 'snapshot_path' not in p['evidence'][0] and 'locator' not in p['evidence'][0]


@pytest.mark.parametrize('change',[{'source_url':'javascript:alert(1)'},{'source_url':'https://evil.example/data.brreg.no'}, {'license':'unknown'}, {'locator':{'organisation_number':'984661185'}}])
def test_invalid_or_wrong_entity_evidence_is_not_exported(change):
    r=row();r['evidence'][0].update(change)
    assert m.profile(r)['claims']==[]


def test_stale_and_personal_contact_fields_are_not_exported():
    r=row();r['claims'][0]['stale_since']='2026-11-13';assert not m.profile(r)['claims']
    r=row();r['claims'][0]['field']='email';assert not m.profile(r)['claims']


def test_existing_export_not_overwritten(tmp_path):
    with pytest.raises(FileExistsError):m.export(tmp_path/'missing.jsonl',tmp_path)
