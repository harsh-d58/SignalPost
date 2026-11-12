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
    families = {"jobs", "website", "social_profiles"} | {c["family"] for cs in company_claims.values() for c in cs}
    rows = [{"organisation_number": org, "claims": cs, "availability": {f: {"state": "available" if any(c["family"] == f for c in cs) else "not_available"} for f in families}} for org, cs in company_claims.items()]
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


def test_reference_website_matches_across_keys_and_deduplicates_labels(tmp_path):
    claim = {"family": "website", "field": "official_website", "value": "https://example.no/", "key": "crawler-id"}
    run_files(tmp_path / "run", {"1": [claim], "2": []})
    pool = tmp_path / "pool.jsonl"
    labels = [
        {**claim, "organisation_number": "1", "key": "review-1", "value": "https://EXAMPLE.no"},
        {**claim, "organisation_number": "1", "key": "review-2"},
        {**claim, "organisation_number": "2", "key": "review-3"},
    ]
    pool.write_text("".join(json.dumps(c) + "\n" for c in labels), encoding="utf-8")
    measured = metrics.measure(tmp_path / "run", pool)["local_pool"]["families"]["website"]
    assert measured["reference_claims"] == 2
    assert measured["matched_claims"] == 1
    assert measured["company_recall"] == .5


@pytest.mark.parametrize("override, expected", [
    ({}, 1),
    ({"account_type": "KONSERN"}, 0),
    ({"account_type": None}, 0),
    ({"period": {"from": "2024-01-01", "to": "2024-12-31"}}, 0),
    ({"unit": "EUR"}, 0),
    ({"field": "profit"}, 0),
])
def test_financial_reference_matches_only_same_field_scope_period_and_currency(tmp_path, override, expected):
    claim = {"family": "financials", "field": "revenue", "key": "crawler-revenue-2025", "value": 5000,
             "period": {"from": "2025-01-01", "to": "2025-12-31"}, "unit": "NOK", "note": "account_type=SELSKAP"}
    run_files(tmp_path / "run", {"1": [claim]})
    pool = tmp_path / "pool.jsonl"
    label = {**claim, "organisation_number": "1", "key": "review-id", "account_type": "SELSKAP", **override}
    label.pop("note")
    pool.write_text(json.dumps(label), encoding="utf-8")
    assert metrics.measure(tmp_path / "run", pool)["local_pool"]["families"]["financials"]["matched_claims"] == expected


def test_reference_articles_and_jobs_match_item_identity(tmp_path):
    news = {"family": "activity", "field": "company_news", "effective_date": "2026-11-10",
            "value": {"url": "https://example.no/news/office", "title": "New office", "date": "2026-11-10"}}
    job = {"family": "jobs", "field": "job_posting", "value": {
        "url": "https://example.no/jobs/ad?id=123", "employer": "Example AS", "title": "Engineer"}}
    run_files(tmp_path / "run", {"1": [news, job]})
    pool = tmp_path / "pool.jsonl"
    labels = [
        {**news, "value": {"url": news["value"]["url"], "title": "Office opens"}, "key": "review-news"},
        {**news, "value": {**news["value"], "date": "2026-11-09"}},
        {**job, "value": {**job["value"], "title": "Engineering role", "employer": "EXAMPLE AS"}},
        {**job, "value": {**job["value"], "employer": "Parent AS"}},
        {**job, "value": {**job["value"], "url": "https://example.no/jobs/ad?id=124"}},
    ]
    pool.write_text("".join(json.dumps({**c, "organisation_number": "1"}) + "\n" for c in labels), encoding="utf-8")
    measured = metrics.measure(tmp_path / "run", pool)["local_pool"]["families"]
    assert (measured["activity"]["matched_claims"], measured["activity"]["reference_claims"]) == (1, 2)
    assert (measured["jobs"]["matched_claims"], measured["jobs"]["reference_claims"]) == (1, 3)


def test_comparison_refuses_different_batches(tmp_path):
    run_files(tmp_path / "a", {"one": []})
    run_files(tmp_path / "b", {"two": []})
    with pytest.raises(ValueError, match="identical"):
        metrics.compare(tmp_path / "a", tmp_path / "b")


def test_stale_claims_are_not_current_coverage(tmp_path):
    run_files(tmp_path / "run", {"one": [{"family": "jobs", "field": "job", "value": "old", "stale_since": "yesterday"}]})
    assert metrics.measure(tmp_path / "run")["families"]["jobs"]["company_coverage"] == 0
