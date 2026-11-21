import json
from datetime import datetime, timezone

from signalpost.evidence import SnapshotStore
from signalpost.http import Snapshot
from signalpost.registry import fetch_activity
from signalpost.update_cursor import EntityUpdateCursor


def test_inclusive_refresh_uses_retained_evidence_and_recovers_from_interruption(tmp_path):
    org = "923609016"
    day = datetime.now(timezone.utc).isoformat()

    class Feed:
        def __init__(self, ids, interrupted=False):
            self.ids = ids
            self.interrupted = interrupted
            self.urls = []

        def get_json(self, url, **kwargs):
            self.urls.append(url)
            data = []
            if "/enheter?" in url:
                if self.interrupted:
                    return Snapshot(url, url, 503, day)
                data = {"_embedded": {"oppdaterteEnheter": [
                    {"organisasjonsnummer": org, "oppdateringsid": uid, "dato": day, "endringstype": "Ny"}
                    for uid in self.ids]}, "page": {"number": 0, "totalPages": 1}}
            return Snapshot(url, url, 200, day, body=json.dumps(data).encode(), content_type="application/json")

    baseline = tmp_path / "baseline"
    cache = EntityUpdateCursor(SnapshotStore(baseline), None, None)
    first, _, errors = fetch_activity(Feed([10, 11]), [org], cursor=cache)
    assert not errors
    digest = cache.store.put(json.dumps(cache.complete).encode())["sha256"]
    (baseline / "run-report.json").write_text(json.dumps(
        {"run_id": "one", "validation": {"passed": True}, "entity_update_cursor": {"sha256": digest}}))

    for interrupted in (True, False):
        restored = EntityUpdateCursor(SnapshotStore(tmp_path / "refresh"), baseline, "one")
        feed = Feed([11, 12], interrupted)
        rows, _, errors = fetch_activity(feed, [org], cursor=restored)
        assert "oppdateringsid=11" in feed.urls[0]
        assert bool(errors) is interrupted
        assert [row["oppdateringsid"] for row, _ in rows[org]] == ([10, 11] if interrupted else [10, 11, 12])
        assert rows[org][0][1].sha256 == first[org][0][1].sha256
        if interrupted:
            assert not restored.complete
        else:
            assert restored.complete[org]["last_id"] == 12

    # A damaged retained page must lead to a complete dated lookup.
    record = cache.complete[org]["pages"][0]
    (baseline / record["object"]["path"]).write_bytes(b"{}")
    repaired = EntityUpdateCursor(SnapshotStore(tmp_path / "repaired"), baseline, "one")
    feed = Feed([10, 11, 12])
    fetch_activity(feed, [org], cursor=repaired)
    assert "&dato=" in feed.urls[0] and repaired.resumed == 0
