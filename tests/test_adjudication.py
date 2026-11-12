import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("adjudication", Path(__file__).resolve().parents[1] / "eval/adjudication.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_judgment_denominators_and_unknowns(tmp_path):
    claims = [{"id": str(i), "family": "website"} for i in range(4)]
    (tmp_path / "envelopes.jsonl").write_text(json.dumps({"organisation_number": "123", "claims": claims}))
    rows = [{"organisation_number": "123", "claim_id": str(i), "judgment": label,
             "reviewer": "independent reviewer", "evidence_url": "https://example.no"}
            for i, label in enumerate(["supported", "wrong_entity", "unresolved"])]
    labels = tmp_path / "labels.jsonl"
    labels.write_text("\n".join(json.dumps(row) for row in rows))
    report = module.summarize(tmp_path, labels)
    assert report["overall"]["precision_on_resolved"] == .5
    assert report["overall"]["supported_fraction_of_reviewed"] == 1 / 3
    assert report["unreviewed_predictions"] == 1
    assert report["recall"] is None
    rows.append(rows[0])
    labels.write_text("\n".join(json.dumps(row) for row in rows))
    with pytest.raises(ValueError, match="unique"):
        module.summarize(tmp_path, labels)


def test_review_queue_is_deterministic_unlabeled_and_not_overwritten(tmp_path):
    spec = importlib.util.spec_from_file_location("prepare_review", Path(__file__).resolve().parents[1] / "eval/prepare_review.py")
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    claims = [{"id": str(i), "family": "website", "field": "official_website", "value": f"https://{i}.example.no", "evidence_ids": []} for i in range(3)]
    (tmp_path / "envelopes.jsonl").write_text(json.dumps({"organisation_number": "123", "claims": claims}))
    first, second = tmp_path / "first", tmp_path / "second"
    result = prepare.prepare(tmp_path, first, per_family=1)
    prepare.prepare(tmp_path, second, per_family=1)
    assert result["tasks"] == 3 and result["labels_completed"] == 0
    assert (first / "judgments.jsonl").read_bytes() == (second / "judgments.jsonl").read_bytes()
    assert all(json.loads(l)["judgment"] is None for l in (first / "judgments.jsonl").read_text().splitlines())
    with pytest.raises(FileExistsError):
        prepare.prepare(tmp_path, first)
