import importlib.util
import json
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / "eval" / "metrics.py"
spec = importlib.util.spec_from_file_location("metrics", path)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def run_files(root, company_claims):
    root.mkdir(exist_ok=True)
    rows = [{"organisation_number": org, "claims": cs, "availability": {f: {"state": "available" if any(c["family"] == f for c in cs) else "not_available"} for f in ("jobs", "website", "social_profiles")}} for org, cs in company_claims.items()]
    (root / "envelopes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in rows))
    (root / "run-report.json").write_text(json.dumps({"run_id": "fixture", "agent_version": "test", "input_count": len(rows), "validation": {"passed": True},
        "operations": {"requests": 0, "elapsed_seconds": 0}, "third_party_cost_usd": 0}))


def test_pool_recall_uses_70_30_and_never_infers_precision(tmp_path):
    companies = {str(i): [] for i in range(20)}
    reference = []
    for i in range(50):
        org = str(i % 20)
        claim = {"family": "jobs", "key": str(i), "field": "job", "value": i}
        reference.append({**claim, "organisation_number": org})
    # 30 correctly matched ads spanning 15 employers, as in the published example.
    for org in list(companies)[:15]:
        companies[org] = [c for c in reference if c["organisation_number"] == org][:2]
    for family in ("website", "social_profiles"):
        reference.append({"organisation_number": "0", "family": family, "key": "one", "field": "one", "value": "x"})
    run_files(tmp_path / "run", companies)
    pool = tmp_path / "pool.jsonl"
    pool.write_text("".join(json.dumps(c) + "\n" for c in reference))
    result = metrics.measure(tmp_path / "run", pool)
    assert result["local_pool"]["families"]["jobs"]["weighted_recall"] == pytest.approx(.705)
    assert result["precision"] is None and result["official_score"] is None


def test_sparse_reference_is_not_zero_recall(tmp_path):
    run_files(tmp_path / "run", {"0": []})
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps({"organisation_number": "0", "family": "jobs", "key": "one", "field": "job", "value": "x"}))
    result = metrics.measure(tmp_path / "run", pool)
    assert result["local_pool"]["sparse_not_measured"]
    assert result["local_pool"]["families"]["jobs"]["weighted_recall"] is None


def test_comparison_refuses_different_batches(tmp_path):
    run_files(tmp_path / "a", {"one": []})
    run_files(tmp_path / "b", {"two": []})
    with pytest.raises(ValueError, match="identical"):
        metrics.compare(tmp_path / "a", tmp_path / "b")


def test_stale_claims_are_not_current_coverage(tmp_path):
    run_files(tmp_path / "run", {"one": [{"family": "jobs", "field": "job", "value": "old", "stale_since": "yesterday"}]})
    assert metrics.measure(tmp_path / "run")["families"]["jobs"]["company_coverage"] == 0
