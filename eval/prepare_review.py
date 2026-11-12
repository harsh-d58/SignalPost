"""Prepare deterministic claim-review tasks; never generate adjudication labels.

python eval/prepare_review.py RUN --out out-review --per-family 20
Web attribution-sensitive claims are all included. Other families use a stable
hash sample. This is a review queue, not a recall pool or a blinded holdout.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

FULL_REVIEW = {"website", "social_profiles", "jobs"}


def prepare(run, out, per_family=20):
    if per_family < 1:
        raise ValueError("per-family must be positive")
    source = run / "envelopes.jsonl"
    raw = source.read_bytes()
    groups = {}
    for line in raw.decode("utf-8").splitlines():
        env = json.loads(line)
        evidence = {e["id"]: e for e in env.get("evidence", [])}
        for claim in env["claims"]:
            if claim.get("availability", "available") != "available" or claim.get("stale_since"):
                continue
            row = {"organisation_number": env["organisation_number"], "claim_id": claim["id"],
                   "family": claim["family"], "field": claim["field"], "claim": claim,
                   "sources": [evidence[eid] for eid in claim.get("evidence_ids", []) if eid in evidence],
                   "reviewer": "", "evidence_url": "", "judgment": None,
                   "review_notes": "", "run_id": env.get("run", {}).get("run_id")}
            bucket = "company_news" if claim["field"] == "company_news" else claim["family"]
            groups.setdefault(bucket, []).append(row)
    rows = []
    for bucket, candidates in sorted(groups.items()):
        candidates.sort(key=lambda r: hashlib.sha256(f"{r['organisation_number']}:{r['claim_id']}".encode()).hexdigest())
        rows.extend(candidates if bucket in FULL_REVIEW or bucket == "company_news" else candidates[:per_family])
    out.mkdir(parents=True, exist_ok=True)
    target = out / "judgments.jsonl"
    # Never overwrite a reviewer's answers on rerun.
    with target.open("x", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    manifest = {"input_sha256": hashlib.sha256(raw).hexdigest(), "tasks": len(rows),
                "families": dict(Counter(r["family"] for r in rows)), "per_family_sample": per_family,
                "labels_completed": 0, "sampling": "all website/social/job/news claims; deterministic hash sample in other families",
                "limitation": "Development review queue only. Not an independent reference pool, population sample or blinded release set."}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-family", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(prepare(args.run, args.out, args.per_family), indent=2))
