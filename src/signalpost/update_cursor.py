"""Resume a complete Brreg entity-event window from privacy-minimized source pages."""
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .evidence import instant
from .http import Snapshot, utc_now


class EntityUpdateCursor:
    def __init__(self, store, previous, previous_id):
        self.store = store
        self.prior = {}
        self.complete = {}
        self.resumed = 0
        if not previous:
            return
        path = Path(previous)
        self.root = path if path.is_dir() else path.parent
        if self.root.name == "history":
            self.root = self.root.parent
        try:
            report = json.loads((self.root / "run-report.json").read_bytes())
            if report["run_id"] == previous_id and report["validation"]["passed"]:
                sha = report["entity_update_cursor"]["sha256"]
                if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
                    return
                raw = (self.root / "snapshots" / sha[:2] / (sha + ".json")).read_bytes()
                if hashlib.sha256(raw).hexdigest() == sha:
                    self.prior = json.loads(raw)
        except (OSError, ValueError, KeyError, TypeError):
            pass  # Older or interrupted runs use the full dated lookup.

    def restore(self, chunk, since):
        state = self.prior.get(chunk)
        if not state:
            return [], {}, 0
        try:
            if instant(state["since"]) > instant(since) or instant(state["observed_at"]) > instant(utc_now()):
                return [], {}, 0
            references = state["pages"]
            if not 0 < len(references) <= 24:
                return [], {}, 0
            events = {}
            high = 0
            for record in references:
                url = record["requested_url"]
                parts = urlsplit(url)
                if (parts.scheme, parts.netloc, parts.path) != ("https", "data.brreg.no", "/enhetsregisteret/api/oppdateringer/enheter"):
                    raise ValueError("unexpected event source")
                if (parse_qs(parts.query).get("organisasjonsnummer") != [chunk] or record["final_url"] != url
                        or record["retention"] != "privacy_minimized_json"):
                    raise ValueError("event scope mismatch")
                saved = self.store.import_record(record, self.root)
                raw = (self.store.root / saved["object"]["path"]).read_bytes()
                body = json.loads(raw)
                snap = Snapshot(url, url, 200, saved["retrieved_at"], sha256=saved["content_sha256"])
                with self.store.lock:
                    self.store.records[(snap.sha256, url)] = saved
                for row in body.get("_embedded", {}).get("oppdaterteEnheter", []):
                    uid = int(row["oppdateringsid"])
                    high = max(high, uid)
                    if instant(row["dato"]) >= instant(since):
                        events[(str(row["organisasjonsnummer"]), uid)] = (row, snap)
            if high != state["last_id"] or high <= 0:
                raise ValueError("cursor does not match retained events")
            self.resumed += 1
            return list(references), events, high
        except (OSError, ValueError, TypeError, KeyError):
            return [], {}, 0

    def save_page(self, snap):
        self.store.capture(snap)
        return self.store.records.get((snap.sha256, snap.url))

    def stage(self, chunk, since, pages, high):
        if high > 0 and pages and all(page and page.get("object") for page in pages):
            self.complete[chunk] = {"last_id": high, "since": since, "observed_at": utc_now(), "pages": pages}
