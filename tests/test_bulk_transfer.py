import gzip
import io
from contextlib import contextmanager
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
import pytest

from signalpost import bulk
from signalpost.budget import Budget


@pytest.mark.parametrize("bad", [
    "123456789,888607862,Example", "123456789", "123456789,888607862,Example,extra",
    ",888607862,Example", "123456789,,Example",
])
def test_invalid_workplace_archive_never_returns_partial_inventory(monkeypatch, bad):
    @contextmanager
    def archive(*args):
        yield io.StringIO("organisasjonsnummer,overordnetEnhet,navn\n123456789,888607862,Example\n" + bad)
    monkeypatch.setattr(bulk, "_text", archive)
    with pytest.raises(ValueError):
        bulk.bulk_subunits({"888607862"}, Budget())


@pytest.mark.parametrize("scenario", ["slow", "feasible", "too_slow", "stalled", "truncated"])
def test_archive_transfer_outcomes(tmp_path, monkeypatch, scenario):
    raw = gzip.compress(b'[{"organisasjonsnummer":"123456789"}]')
    payload = raw[:-5] if scenario == "truncated" else raw
    clock = [0]

    class Response:
        is_redirect = False
        status_code = 200
        headers = {"content-length": str(len(payload))}

        def raise_for_status(self):
            pass

        def iter_raw(self):
            if scenario == "stalled":
                raise httpx.ReadTimeout("fixture timeout")
            split = {"feasible": len(payload) // 2, "too_slow": 1}.get(scenario, len(payload) - 1)
            clock[0] = 181 if scenario in {"slow", "feasible", "too_slow"} else 2
            yield payload[:split]
            yield payload[split:]

    @contextmanager
    def stream(*args, **kwargs):
        yield Response()

    monkeypatch.setattr(bulk.httpx, "stream", stream)
    monkeypatch.setattr(bulk, "check_url", urlsplit)
    monkeypatch.setattr(bulk, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(bulk.tempfile, "tempdir", str(tmp_path))
    budget = Budget(max_seconds=2700)
    progress = {}
    if scenario in {"slow", "feasible"}:
        assert "123456789" in bulk.bulk_roles({"123456789"}, budget, progress)
        assert progress["deadline_extended"] and progress["received_bytes"] == len(raw)
        assert progress["last_progress_at"]
    else:
        from signalpost.budget import BudgetExhausted
        with pytest.raises({"stalled": httpx.ReadTimeout, "truncated": EOFError, "too_slow": BudgetExhausted}[scenario]):
            bulk.bulk_roles({"123456789"}, budget, progress)
        assert progress["stage"] == ("parse" if scenario == "truncated" else "download")
    assert not list(tmp_path.iterdir())


def test_incomplete_roles_archive_does_not_establish_absence(tmp_path, monkeypatch):
    from signalpost.pipeline import Runner
    from signalpost.http import Snapshot
    from signalpost.registry import ROLES_URL, SUBUNITS_URL, roles_claims, subunit_claims

    org = "923609016"
    r = Runner([org], out_dir=tmp_path, run_id="partial", bulk=None, previous=None, bulk_files=True,
               max_requests=100, max_minutes=10, max_cost=0, workers=1, job_days=7, web=False)
    calls = []
    def unavailable(url, **kwargs):
        calls.append(url)
        return Snapshot(url, url, 503, "2026-11-20T00:00:00Z")
    monkeypatch.setattr(r.fetcher, "get_json", unavailable)
    try:
        r.bulk.update(roles=None, locations={})
        profile = r.builders[org]
        r._official_step(profile, org, "leadership", "roles", ROLES_URL, roles_claims)
        r._official_step(profile, org, "locations", "locations", SUBUNITS_URL, subunit_claims)
        assert calls == [ROLES_URL.format(org=org)]
        assert profile.families["leadership"].state == "failed"
        assert profile.families["locations"].state == "not_available"
    finally:
        r.fetcher.close()
