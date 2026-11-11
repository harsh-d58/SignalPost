"""Large-batch mode: Brreg nightly bulk files (one request each) instead of one request per company.

* roles:     /roller/totalbestand  (gzipped JSON array, same object shape as /enheter/{org}/roller)
* sub-units: /underenheter/lastned/csv (gzipped CSV, filtered on overordnetEnhet)
Both are streamed; only rows for the batch are kept. Results are wrapped as Snapshots so the normal
claim builders (roles_claims / subunit_claims) are reused unchanged.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import tempfile
import time
from typing import Any
from contextlib import contextmanager
from urllib.parse import urljoin

import httpx

from .budget import Budget, BudgetExhausted
from .http import USER_AGENT, Snapshot, utc_now, check_url, MAX_REDIRECTS
from .registry import ROLES_URL, SUBUNITS_URL, _unflatten

ROLES_BULK = "https://data.brreg.no/enhetsregisteret/api/roller/totalbestand"
SUBUNITS_BULK = "https://data.brreg.no/enhetsregisteret/api/underenheter/lastned/csv"


def _download(url: str, budget: Budget, phase: str, accept: str, attempts: int = 2, metadata: dict | None = None) -> str:
    fd, path = tempfile.mkstemp(suffix=".gz", prefix="signalpost-bulk-")
    os.close(fd)
    deadline = time.monotonic() + min(480.0, max(0.0, budget.time_left() - 90))
    try:
        for attempt in range(attempts):
            current = url
            try:
                for _ in range(MAX_REDIRECTS + 1):
                    if time.monotonic() >= deadline:
                        raise BudgetExhausted("bulk download deadline")
                    parts = check_url(current)
                    budget.acquire(parts.hostname or "", phase)
                    with httpx.stream("GET", current, headers={"User-Agent": USER_AGENT, "Accept": accept},
                                      timeout=max(0.1, min(30.0, budget.time_left(), deadline - time.monotonic())), follow_redirects=False) as response:
                        if response.is_redirect and response.headers.get("location"):
                            current = urljoin(current, response.headers["location"])
                            continue
                        response.raise_for_status()
                        size = 0
                        digest = hashlib.sha256()
                        with open(path, "wb") as handle:
                            for chunk in response.iter_raw():
                                if budget.time_left() <= 0 or time.monotonic() >= deadline:
                                    raise BudgetExhausted("bulk download time budget exhausted")
                                size += len(chunk)
                                if size > 2_000_000_000:
                                    raise ValueError("bulk download exceeds 2 GB")
                                handle.write(chunk)
                                digest.update(chunk)
                        if metadata is not None:
                            metadata.update(source_url=url, final_url=current, archive_sha256=digest.hexdigest(),
                                            archive_bytes=size, retrieved_at=utc_now(), status=response.status_code)
                        return path
                raise ValueError("too many bulk redirects")
            except (httpx.HTTPError, OSError):
                if attempt + 1 == attempts:
                    raise
        raise RuntimeError("bulk download failed")
    except BaseException:
        os.unlink(path)
        raise


@contextmanager
def _text(url: str, budget: Budget, phase: str, accept: str):
    metadata = {}
    path = _download(url, budget, phase, accept, metadata=metadata)
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as text:
            text.source_metadata = metadata
            yield text
    finally:
        os.unlink(path)


def _snap(url: str, obj: Any, provenance: dict | None = None) -> Snapshot:
    body = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return Snapshot(url, url, 200, (provenance or {}).get("retrieved_at") or utc_now(), body=body,
                    content_type="application/json", sha256=hashlib.sha256(body).hexdigest(), provenance=provenance or {})


def _json_array(text):
    """Stream JSON objects without depending on key order or chunk boundaries."""
    decoder = json.JSONDecoder()
    buf = ""
    pos = 0
    started = False
    eof = False
    expect_value = True
    any_value = False
    while True:
        while pos < len(buf) and buf[pos].isspace():
            pos += 1
        if pos < len(buf):
            if not started:
                if buf[pos] != "[":
                    raise ValueError("roles bulk file is not a JSON array")
                started = True
                pos += 1
                continue
            if buf[pos] == "]":
                if expect_value and any_value:
                    raise ValueError("trailing comma in roles bulk file")
                if buf[pos + 1:].strip() or any(chunk.strip() for chunk in iter(lambda: text.read(1 << 20), "")):
                    raise ValueError("trailing data in roles bulk file")
                return
            if not expect_value:
                if buf[pos] != ",":
                    raise ValueError("missing JSON array separator")
                pos += 1
                expect_value = True
                continue
            try:
                value, end = decoder.raw_decode(buf, pos)
            except json.JSONDecodeError:
                pass  # incomplete record, append one bounded chunk below
            else:
                if not isinstance(value, dict):
                    raise ValueError("roles bulk entry is not an object")
                yield value
                any_value = True
                pos = end
                expect_value = False
                continue
        if eof:
            raise ValueError("truncated roles bulk file")
        buf = buf[pos:]
        pos = 0
        if len(buf) > 20_000_000:
            raise ValueError("roles bulk record exceeds size limit")
        chunk = text.read(1 << 20)
        eof = not chunk
        buf += chunk


def bulk_roles(orgs: set[str], budget: Budget) -> dict[str, Snapshot]:
    found: dict[str, Snapshot] = {}
    deadline = time.monotonic() + 600
    with _text(ROLES_BULK, budget, "roles", "application/json") as text:
        metadata = dict(getattr(text, "source_metadata", {}))
        for row in _json_array(text):
            if budget.time_left() <= 0 or time.monotonic() >= deadline:
                raise BudgetExhausted("bulk parse time budget exhausted")
            href = ((row.get("_links") or {}).get("self") or {}).get("href", "")
            match = re.fullmatch(r"https://data\.brreg\.no/enhetsregisteret/api/enheter/(\d{9})/roller", href)
            org = str(row.get("organisasjonsnummer") or (match.group(1) if match else ""))
            if match and row.get("organisasjonsnummer") and str(row["organisasjonsnummer"]) != match.group(1):
                raise ValueError("conflicting role entity identifiers")
            if org in orgs:
                if org in found:
                    raise ValueError("duplicate role entity in bulk file")
                found[org] = _snap(ROLES_BULK, row, {**metadata, "kind": "bulk_selected_record",
                                   "organisation_number": org, "transformation": "selected_role_object_json"})
    return found


def bulk_subunits(orgs: set[str], budget: Budget) -> dict[str, Snapshot]:
    units: dict[str, list[dict[str, Any]]] = {}
    deadline = time.monotonic() + 600
    with _text(SUBUNITS_BULK, budget, "locations", "application/vnd.brreg.enhetsregisteret.underenhet.v2+gzip;charset=UTF-8") as text:
        metadata = dict(getattr(text, "source_metadata", {}))
        reader = csv.DictReader(text)
        if not {"organisasjonsnummer", "overordnetEnhet"} <= set(reader.fieldnames or []):
            raise ValueError("subunit bulk file missing required columns")
        for row in reader:
            if budget.time_left() <= 0 or time.monotonic() >= deadline:
                raise BudgetExhausted("bulk parse time budget exhausted")
            parent = row.get("overordnetEnhet")
            if parent in orgs:
                units.setdefault(parent, []).append(_unflatten(row))
    return {org: _snap(SUBUNITS_BULK, {"_embedded": {"underenheter": rows}},
                      {**metadata, "kind": "bulk_selected_records", "organisation_number": org,
                       "transformation": "CSV rows filtered by overordnetEnhet, unflattened JSON"}) for org, rows in units.items()}
