import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from signalpost.http import Snapshot
from signalpost.pipeline import Runner, read_inputs
from signalpost.web import valid_orgnr


def numbers(count):
    result = []
    candidate = 900000000
    while len(result) < count:
        if valid_orgnr(str(candidate)):
            result.append(str(candidate))
        candidate += 1
    return result


@pytest.mark.parametrize("size", [0, 1, 100, 1000, 1100])
def test_complete_batch_under_budget_with_random_source_failures(tmp_path, monkeypatch, size):
    orgs = numbers(size)
    runner = Runner(orgs, out_dir=tmp_path, run_id="fixture", bulk=None, previous=None,
                    max_requests=2000, max_minutes=45, max_cost=10, workers=8, job_days=7, web=False, log=lambda *_: None)
    monkeypatch.setattr("signalpost.pipeline.pace_history", lambda: None)
    def feed():
        runner.job_feed.complete = True
        runner.job_feed.done.set()
    monkeypatch.setattr(runner.job_feed, "start", feed)
    def get_json(url, phase, **kw):
        runner.budget.acquire("data.brreg.no", phase)
        if phase == "registry":
            requested = parse_qs(urlsplit(url).query)["organisasjonsnummer"][0].split(",")
            value = {"_embedded": {"enheter": [{"organisasjonsnummer": o, "navn": "Fixture " + o + " AS", "erIKonsern": False} for o in requested]}}
        elif phase == "activity":
            value = [] if "/roller?" in url else {"_embedded": {"oppdaterteEnheter": []}, "page": {"totalPages": 1}}
        elif phase == "accounts":
            o = url.rsplit("/", 1)[-1]
            if int(o) % 7 == 0:
                return Snapshot(url, url, 500, "2026-11-08T00:00:00Z")
            if int(o) % 11 == 0:
                return Snapshot(url, url, 200, "2026-11-08T00:00:00Z", body=b"malformed")
            value = [{"organisasjonsnummer": o, "regnskapsperiode": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
                      "valuta": "NOK", "eiendeler": {"sumEiendeler": 0}}]
        else:
            return Snapshot(url, url, 404, "2026-11-08T00:00:00Z")
        return Snapshot(url, url, 200, "2026-11-08T00:00:00Z", body=json.dumps(value).encode(), sha256="a" * 64)
    monkeypatch.setattr(runner.fetcher, "get_json", get_json)
    try:
        report = runner.run()
    finally:
        runner.finished.set()
        runner.fetcher.close()
    rows = [json.loads(line) for line in (tmp_path / "envelopes.jsonl").read_text().splitlines()]
    assert [row["organisation_number"] for row in rows] == orgs
    assert report["validation"]["passed"]
    assert report["operations"]["requests"] <= 2000
    assert all(row["run"]["terminal_status"] == "completed" for row in rows)


@pytest.mark.parametrize("size", [100, 1000, 1100])
def test_web_budget_is_reserved_at_all_evaluation_sizes(tmp_path, size):
    runner = Runner(numbers(size), out_dir=tmp_path, run_id="fixture", bulk=None, previous=None,
                    max_requests=2000, max_minutes=45, max_cost=10, workers=8, job_days=7)
    try:
        assert runner.plan["web"] >= 400
        assert sum(runner.budget.phase_caps.values()) <= runner.budget.usable_requests
    finally:
        runner.fetcher.close()


@pytest.mark.parametrize("body,expected", [
    ('{\n "organisation_numbers": ["923609016", "984661185"]\n}', ["923609016", "984661185"]),
    ('{"organisation_numbers": []}', []),
    ('\ufeff[923609016, "984661185"]', ["923609016", "984661185"]),
    ('{"organisation_number":"923609016"}\n{"organisation_number":"984661185"}', ["923609016", "984661185"]),
])
def test_input_formats(tmp_path, body, expected):
    p = tmp_path / "batch.json"
    p.write_text(body, encoding="utf-8")
    assert read_inputs(p) == expected


def test_history_archive_contains_path_and_preserves_reused_id(tmp_path):
    from signalpost.cli import archive_previous
    p = tmp_path / "envelopes.jsonl"
    p.write_text(json.dumps({"run": {"run_id": "../../elsewhere"}, "value": 1}), encoding="utf-8")
    _, first = archive_previous(tmp_path)
    assert first.resolve().parent == (tmp_path / "history").resolve()
    p.write_text(json.dumps({"run": {"run_id": "../../elsewhere"}, "value": 2}), encoding="utf-8")
    _, second = archive_previous(tmp_path)
    assert first != second and first.exists() and second.exists()


def test_blank_evidence_cannot_pass_validation():
    from signalpost.pipeline import validate
    from signalpost.model import FAMILIES
    env = {"organisation_number": "923609016", "availability": {f: {"state": "not_available"} for f in FAMILIES},
           "claims": [], "evidence": [{"id": "e", "source_url": "https://source.no", "retrieved_at": "today", "content_sha256": "a" * 64}]}
    assert not validate([env], ["923609016"])["passed"]
