"""Summarize independent per-claim judgments without treating predictions as labels.

python eval/adjudication.py RUN judgments.jsonl --output report.json
Rows require organisation_number, claim_id, reviewer, evidence_url, judgment.
Allowed judgments: supported, wrong_entity, wrong_value, unsupported, unresolved.
"""
import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

JUDGMENTS = {"supported", "wrong_entity", "wrong_value", "unsupported", "unresolved"}


def interval(successes, total):
    if not total:
        return None
    z = 1.96
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def summarize(run, judgments):
    predictions = {}
    stale = 0
    for line in (run / "envelopes.jsonl").read_text(encoding="utf-8").splitlines():
        env = json.loads(line)
        for claim in env["claims"]:
            if claim.get("availability", "available") != "available":
                continue
            if claim.get("stale_since"):
                stale += 1
                continue
            predictions[(env["organisation_number"], claim["id"])] = claim
    groups = defaultdict(Counter)
    seen = set()
    for line in judgments.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row["organisation_number"], row["claim_id"])
        if key not in predictions or key in seen:
            raise ValueError("Judgment must identify one unique current prediction")
        if row.get("judgment") not in JUDGMENTS or not row.get("reviewer") or not row.get("evidence_url"):
            raise ValueError("Judgment needs a valid outcome, reviewer and evidence URL")
        seen.add(key)
        groups[predictions[key]["family"]][row["judgment"]] += 1
    def result(counts):
        reviewed = sum(counts.values())
        resolved = reviewed - counts["unresolved"]
        correct = counts["supported"]
        return {"judgments": dict(counts), "reviewed": reviewed, "resolved": resolved,
                "precision_on_resolved": correct / resolved if resolved else None,
                "precision_wilson_95": interval(correct, resolved),
                "supported_fraction_of_reviewed": correct / reviewed if reviewed else None,
                "wrong_entity_count": counts["wrong_entity"]}
    total = Counter()
    for counts in groups.values():
        total.update(counts)
    return {"current_predictions": len(predictions), "stale_predictions_excluded": stale,
            "unreviewed_predictions": len(predictions) - len(seen), "overall": result(total),
            "families": {f: result(c) for f, c in sorted(groups.items())},
            "recall": None, "official_score": None,
            "limitation": "Reviewer-supplied sample only. Independence and representativeness require external review. No recall or F1 without a compatible independent reference pool."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("judgments", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = summarize(args.run, args.judgments)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
