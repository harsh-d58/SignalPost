"""Private, content-addressed evidence artifacts. Never copied to the showcase.

Open registry responses are retained as privacy-minimized JSON. Company pages
and NAV responses retain only the published excerpt, not raw pages or contacts.
The original response digest and retained-object digest are deliberately distinct.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .model import stable_id

PARSER_VERSION = "signalpost-evidence/2"
PRIVATE_KEYS = {"foedselsdato", "fodselsdato", "fødselsdato", "birthdate", "birth_date",
                "foedselsnummer", "personnummer", "contacts", "contactlist", "kontaktpersoner",
                "epostadresse", "telefon", "mobil", "telefonnummer"}


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def minimize(value):
    if isinstance(value, dict):
        return {k: minimize(v) for k, v in value.items() if k.casefold() not in PRIVATE_KEYS}
    if isinstance(value, list):
        return [minimize(v) for v in value]
    return value


class SnapshotStore:
    def __init__(self, root: Path):
        self.root = root
        self.records: dict[tuple[str, str], dict] = {}
        self.lock = threading.RLock()

    def put(self, body: bytes) -> dict:
        digest = hashlib.sha256(body).hexdigest()
        relative = f"snapshots/{digest[:2]}/{digest}.json"
        path = self.root / relative
        with self.lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("existing evidence object failed digest validation")
            else:
                temporary = path.with_suffix(".tmp")
                temporary.write_bytes(body)
                temporary.replace(path)
        return {"path": relative, "sha256": digest, "bytes": len(body)}

    def capture(self, snap) -> None:
        # Never retain tokens or authenticated response headers.
        if "/publicToken" in snap.url:
            return
        if snap.body:
            snap.sha256 = hashlib.sha256(snap.body).hexdigest()
        if not snap.sha256:
            return
        key = (snap.sha256, snap.url)
        with self.lock:
            if key in self.records:
                return
        host = urlsplit(snap.url).hostname
        record = {"id": stable_id("snapshot", snap.url, snap.sha256),
                  "requested_url": snap.url, "final_url": snap.final_url,
                  "redirects": snap.redirects, "status": snap.status,
                  "retrieved_at": snap.retrieved_at, "content_sha256": snap.sha256,
                  "content_type": snap.content_type, "parser_version": PARSER_VERSION,
                  "error": snap.error, "access_policy": "permitted-source-excerpt",
                  "retention": "excerpt_only", "source_class": "company_owned"}
        if host == "data.brreg.no" and snap.ok:
            try:
                body = json.dumps(minimize(snap.json()), ensure_ascii=False, sort_keys=True).encode("utf-8")
            except (ValueError, UnicodeError):
                pass
            else:
                record.update(object=self.put(body), retention="privacy_minimized_json",
                              access_policy="NLOD-2.0", source_class="official_registry")
        if host == "pam-stilling-feed.nav.no":
            record.update(access_policy="NAV-credential-required", source_class="public_api")
        if getattr(snap, "provenance", None):
            record["provenance"] = snap.provenance
            if snap.provenance.get("kind") == "supplied_registry_row":
                record.update(requested_url=None, final_url=None, status=None,
                              source_identifier=f"urn:sha256:{snap.provenance['input_sha256']}#organisation/{snap.provenance['organisation_number']}")
        with self.lock:
            self.records[key] = record
            self.records[(snap.sha256, snap.final_url)] = record

    def bind(self, evidence: dict) -> dict | None:
        key = (evidence["content_sha256"], evidence["source_url"])
        with self.lock:
            source = self.records.get(key)
        if not source:
            return None
        record = dict(source)
        if evidence["extraction_method"].rsplit(":", 1)[-1].casefold() in PRIVATE_KEYS:
            record.pop("object", None)
            record["retention"] = "excerpt_only"
            record["retention_reason"] = "contact fields removed from retained registry JSON; published business contact excerpt only"
        if "object" not in record:
            # An excerpt is a reproducible extraction artifact, not a full-page replay.
            body = json.dumps({"source_url": evidence["source_url"],
                               "content_sha256": evidence["content_sha256"],
                               "claim_span": evidence["claim_span"],
                               "extraction_method": evidence["extraction_method"]},
                              ensure_ascii=False, sort_keys=True).encode("utf-8")
            record["object"] = self.put(body)
            record["id"] = stable_id("excerpt", source["id"], record["object"]["sha256"])
        evidence["snapshot_id"] = record["id"]
        if record.get("source_identifier"):
            evidence["source_identifier"] = record["source_identifier"]
        evidence.setdefault("locator", {"type": "text_quote", "exact": evidence["claim_span"],
                                        "method": evidence["extraction_method"]})
        evidence["parser_version"] = PARSER_VERSION
        return record

    def import_record(self, record: dict, previous_root: Path) -> dict:
        """Carry retained artifacts into a new run without accepting path traversal."""
        obj = record.get("object") or {}
        relative = obj.get("path", "")
        root = previous_root.resolve()
        path = (root / relative).resolve()
        if not relative or not path.is_relative_to(root):
            raise ValueError("invalid prior snapshot path")
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != obj.get("sha256"):
            raise ValueError("prior evidence digest mismatch")
        return {**record, "object": self.put(body)}
