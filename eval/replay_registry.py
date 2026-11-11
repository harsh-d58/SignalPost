"""Reparse identity/workplace artifacts without another crawl, preserving live provenance.

uv run python eval/replay_registry.py out-live out-replay
This is explicitly an offline parser replay, not a new live benchmark. It refuses
unexpected claim changes and keeps the original live report and source timestamps.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from signalpost.http import Snapshot, utc_now
from signalpost.model import ProfileBuilder
from signalpost.pipeline import code_digest, git_version, validate
from signalpost.registry import entity_claims, subunit_claims
from signalpost.synthesis import build_brief


def replay(source: Path, target: Path):
    started = time.monotonic()
    if source.resolve() == target.resolve():
        raise ValueError("replay output must differ from original live artifacts")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / "snapshots", target / "snapshots", dirs_exist_ok=True)
    originals = [json.loads(line) for line in (source / "envelopes.jsonl").read_text(encoding="utf-8").splitlines()]
    cache = {}
    envelopes = []
    normalizations = []
    revision, version = code_digest(), git_version()
    for original in originals:
        env = copy.deepcopy(original)
        org = env["organisation_number"]
        pb = ProfileBuilder(org)
        bindings = {}
        for record in env.get("source_snapshots", []):
            related = [e for e in env["evidence"] if e.get("snapshot_id") == record["id"]]
            methods = {e["extraction_method"] for e in related}
            is_entity = any(m.startswith(("brreg_enheter_api:", "frozen_registry_row:")) for m in methods)
            is_location = "brreg_underenheter_api:overordnetEnhet" in methods
            if not (is_entity or is_location) or record.get("retention") != "privacy_minimized_json":
                continue
            obj = record["object"]
            path = (source / obj["path"]).resolve()
            if not path.is_relative_to(source.resolve()):
                raise ValueError("unsafe source artifact path")
            if obj["path"] not in cache:
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != obj["sha256"]:
                    raise ValueError("source artifact digest mismatch")
                cache[obj["path"]] = raw
            raw = cache[obj["path"]]
            url = related[0]["source_url"]
            snap = Snapshot(url, url, 200, record["retrieved_at"], body=raw, sha256=record["content_sha256"], content_type="application/json")
            if is_entity:
                data = snap.json()
                rows = data.get("_embedded", {}).get("enheter", [data])
                row = next(r for r in rows if str(r.get("organisasjonsnummer")) == org)
                method = next(m.split(":")[0] for m in methods if m.startswith(("brreg_enheter_api:", "frozen_registry_row:")))
                entity_claims(pb, row, retrieved_at=snap.retrieved_at, source_class=related[0]["source_class"], method=method, snapshot=snap)
            else:
                subunit_claims(pb, snap)
            for ev in pb.evidence.values():
                if ev.content_sha256 == snap.sha256 and ev.source_url == url:
                    bindings[ev.id] = record["id"]
        replacements = {(c.family, c.key): c.to_dict() for c in pb.claims.values()}
        evidence = {e["id"]: e for e in env["evidence"]}
        for index, old in enumerate(env["claims"]):
            replacement = replacements.get((old["family"], old.get("key")))
            if not replacement:
                continue
            if old["value"] != replacement["value"]:
                before = old["value"]
                expected = dict(before) if isinstance(before, dict) else before
                if old["family"] == "locations" and isinstance(expected, dict):
                    expected["address"] = ", ".join(str(expected.get("address", "")).splitlines())
                if expected != replacement["value"]:
                    raise ValueError(f"unexpected parser value change: {org} {old['field']}")
                normalizations.append({"organisation_number": org, "field": old["field"], "kind": "address_line_separator"})
            for name in ("first_seen", "last_seen", "times_seen", "stale_since"):
                if name in old:
                    replacement[name] = old[name]
            env["claims"][index] = replacement
            for eid in replacement["evidence_ids"]:
                ev = pb.evidence[eid].to_dict()
                ev.update(snapshot_id=bindings[eid], parser_version="signalpost-evidence/2")
                evidence[eid] = ev
        env["evidence"] = list(evidence.values())
        env["brief"] = build_brief(env)
        env["run"].update(replay_code_sha256=revision, replay_agent_version=version)
        envelopes.append(env)
    output = "".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n" for e in envelopes)
    (target / "envelopes.jsonl").write_text(output, encoding="utf-8")
    live = json.loads((source / "run-report.json").read_text(encoding="utf-8"))
    report = copy.deepcopy(live)
    report["mode"] = "retained_source_replay"
    report["validation"] = validate(envelopes, [e["organisation_number"] for e in originals])
    report["replay"] = {"source_run_id": live["run_id"], "input_envelopes_sha256": hashlib.sha256((source / "envelopes.jsonl").read_bytes()).hexdigest(),
                        "code_sha256": revision, "completed_at": utc_now(), "requests": 0,
                        "seconds": round(time.monotonic() - started, 2), "normalizations": normalizations,
                        "note": "Operations and coverage above belong to the original live collection. This replay repairs extraction locators and normalizes address line separators using retained sources. Observation timestamps are unchanged."}
    (target / "run-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(source / "run-report.json", target / "original-live-run-report.json")
    print(json.dumps({"envelopes": len(envelopes), "normalizations": len(normalizations), "passed": report["validation"]["passed"], "replay_seconds": report["replay"]["seconds"]}))


if __name__ == "__main__":
    replay(Path(sys.argv[1]), Path(sys.argv[2]))
