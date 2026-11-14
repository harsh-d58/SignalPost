"""Build a dated, registry-only public sample from a freshly audited run.

External claims stay in the research run/review queue until independently
adjudicated. This export is not a fresh run or a measured accuracy benchmark.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from export_jbox_data import profile
from signalpost.model import FAMILIES
from signalpost.pipeline import validate
from signalpost.synthesis import build_brief


def export(source: Path, output: Path, count: int = 1000):
    if output.exists():
        raise FileExistsError('Choose a fresh export directory')
    original = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
    rows = []
    for env in original:
        selected = profile(env)
        if not selected['name']:
            continue
        ids = {c['id'] for c in selected['claims']}
        claims = [c for c in env['claims'] if c['id'] in ids]
        refs = {eid for c in claims for eid in c['evidence_ids']}
        evidence = [e for e in env['evidence'] if e['id'] in refs]
        snapshots = {e.get('snapshot_id') for e in evidence}
        row = {'organisation_number': env['organisation_number'], 'name': selected['name'],
               'identity': {c['field']: c['value'] for c in claims if c['family'] == 'identity'},
               'run': env['run'], 'claims': claims, 'evidence': evidence,
               'source_snapshots': [s for s in env.get('source_snapshots', []) if s['id'] in snapshots],
               'availability': {family: {'state': 'available' if any(c['family'] == family for c in claims) else 'not_available',
                    'reason': 'Selected official-registry facts in a dated public sample. Omitted fields are not absence claims.'}
                    for family in FAMILIES},
               'changes': [], 'refresh': {'mode': 'public_sample'}, 'errors': [], 'unpublished_candidates': [],
               'public_sample': {'policy': 'selected-registry-facts-only', 'source_run_id': env['run']['run_id']}}
        row['brief'] = build_brief(row)
        rows.append(row)
        if len(rows) == count:
            break
    if len(rows) != count:
        raise ValueError(f'Need {count} supported identities; found {len(rows)}')
    validation = validate(rows, [r['organisation_number'] for r in rows])
    if not validation['passed']:
        raise ValueError(validation)
    raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()
    output.mkdir(parents=True)
    (output/'envelopes.jsonl').write_bytes(raw)
    (output/'envelopes.jsonl.gz').write_bytes(gzip.compress(raw, mtime=0))
    manifest = {'mode': 'public_sample', 'run_id': 'public-sample-20261114', 'input_count': len(rows),
                'emitted_envelopes': len(rows), 'agent_version': rows[0]['run'].get('agent_version'),
                'code_sha256': rows[0]['run'].get('code_sha256'),
                'started_at': rows[0]['run'].get('started_at'), 'completed_at': rows[0]['run'].get('completed_at'),
                'source_run_id': rows[0]['run']['run_id'], 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'output_sha256': hashlib.sha256(raw).hexdigest(), 'validation': validation,
                'sample_policy': 'Only selected exact-key NLOD registry facts. External facts await independent review.',
                'notes': ['Derived public display sample, not an independently scored research run. Source snapshots remain in the private run directory.'],
                'models': [], 'third_party_cost_usd': 0, 'family_states': {}, 'coverage': {}}
    for family in FAMILIES:
        available = sum(r['availability'][family]['state'] == 'available' for r in rows)
        manifest['family_states'][family] = {'available': available, 'not_available': len(rows)-available}
        manifest['coverage'][family] = available / len(rows)
    (output/'run-report.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--count', type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.out, args.count), indent=2))
