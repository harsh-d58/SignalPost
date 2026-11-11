"""Official Norwegian registry sources (Brønnøysundregistrene, NLOD 2.0).

All facts here are keyed by the organisation number itself, so identity is exact by construction.
Values are copied verbatim from the API; nothing is imputed. Missing => explicit state, never zero.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .budget import BudgetExhausted
from .http import Fetcher, Snapshot
from .model import Claim, Evidence, ProfileBuilder

API = "https://data.brreg.no/enhetsregisteret/api"
ENTITY_URL = API + "/enheter/{org}"
ROLES_URL = API + "/enheter/{org}/roller"
SUBUNITS_URL = API + "/underenheter?overordnetEnhet={org}&size=200"
GROUP_URL = API + "/konsernstruktur/{org}"
ACCOUNTS_URL = "https://data.brreg.no/regnskapsregisteret/regnskap/{org}"
HISTORY_URL = "https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{org}/aar"
HISTORY_PDF = "https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{org}/{year}"
_history_lock = __import__("threading").Lock()
_history_last = [0.0]


def pace_history(interval: float = 2.1) -> None:
    """The filing-copy endpoint allows ~30 request starts per minute; keep starts >= 2.1 s apart (global)."""
    import time
    with _history_lock:
        wait = _history_last[0] + interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _history_last[0] = time.monotonic()
ENTITY_UPDATES_URL = API + "/oppdateringer/enheter?organisasjonsnummer={orgs}&dato={since}&size={size}&includeChanges=true"
ROLE_UPDATES_URL = API + "/oppdateringer/roller?organisasjonsnummer={orgs}&afterTime={since}&size={size}"
NLOD = "NLOD-2.0"


def canonical_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def span(key: str, value: Any) -> str:
    return f'"{key}": {json.dumps(value, ensure_ascii=False)}'


def _get(obj: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def fmt_address(addr: dict[str, Any] | None) -> str | None:
    if not isinstance(addr, dict):
        return None
    # CSV joins address lines with newlines; JSON returns an array. Render both identically.
    lines = [part.strip() for line in (addr.get("adresse") or []) if isinstance(line, str)
             for part in line.splitlines() if part.strip()]
    tail = " ".join(x for x in [addr.get("postnummer"), addr.get("poststed")] if x)
    parts = lines + ([tail] if tail else [])
    if addr.get("land") and addr.get("landkode") not in (None, "NO"):
        parts.append(addr["land"])
    return ", ".join(parts) or None


# ---------------------------------------------------------------------------------------------
# Bulk snapshot (frozen registry snapshot supplied by the evaluator, or Brreg's nightly CSV)
# ---------------------------------------------------------------------------------------------

def _unflatten(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key is None or value in (None, ""):
            continue
        target = out
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
            if not isinstance(target, dict):
                break
        else:
            leaf = parts[-1]
            if leaf == "adresse" and isinstance(value, str):
                target[leaf] = [x.strip() for x in value.split(",") if x.strip()]
            elif value in ("true", "false"):
                target[leaf] = value == "true"
            elif leaf in ("antallAnsatte",):
                try:
                    target[leaf] = int(value)
                except ValueError:
                    pass
            else:
                target[leaf] = value
    return out


BULK_ALIASES = {
    "registreringsdatoenhetsregisteret": "registreringsdatoEnhetsregisteret",
    "registrertIMvaRegisteret": "registrertIMvaregisteret",
    "registreringsdatoantallansatteNAVAaregisteret": "registreringsdatoAntallAnsatteNAVAaregisteret",
}


def bulk_entity(row: dict[str, Any]) -> dict[str, Any]:
    """Make an unflattened bulk-CSV row look like an API entity."""
    out = dict(row)
    for old, new in BULK_ALIASES.items():
        if old in out and new not in out:
            out[new] = out.pop(old)
    for key in ("vedtektsfestetFormaal", "aktivitet"):
        if isinstance(out.get(key), str):
            out[key] = [out[key]]
    capital = out.get("kapital")
    if isinstance(capital, dict) and isinstance(capital.get("belop"), str):
        try:
            capital["belop"] = float(capital["belop"])
        except ValueError:
            capital.pop("belop")
    return out


def _open_text(path: Path):
    raw = path.open("rb")
    head = raw.read(2)
    raw.seek(0)
    if head == b"\x1f\x8b":
        return io.TextIOWrapper(gzip.GzipFile(fileobj=raw), encoding="utf-8-sig", newline="")
    return io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")


def load_bulk(path: str | Path, orgs: Iterable[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Stream a Brreg entity snapshot (CSV/JSON, optionally gzipped) and keep only requested orgs."""
    path = Path(path)
    wanted = set(orgs)
    found: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    with _open_text(path) as text:
        first = text.read(1)
        while first and first.isspace():
            first = text.read(1)
        text_rest = text
        if first in ("[", "{"):
            if path.name.removesuffix(".gz").endswith(".jsonl"):
                rows = (json.loads(line) for line in _chain(first, text_rest) if line.strip())
            else:
                data = json.loads(first + text_rest.read())
                rows = data if isinstance(data, list) else ([data] if "organisasjonsnummer" in data else _get(data, "_embedded", "enheter") or [])
            for row in rows:
                org = str(row.get("organisasjonsnummer", ""))
                if org in wanted:
                    if org in found and found[org] != row:
                        raise ValueError(f"conflicting frozen identity records: {org}")
                    found[org] = row
        else:
            reader = csv.DictReader(_chain(first, text_rest))
            for row in reader:
                org = (row.get("organisasjonsnummer") or "").strip()
                if org in wanted:
                    if org in found:
                        raise ValueError(f"duplicate frozen identity record: {org}")
                    found[org] = bulk_entity(_unflatten(row))
    return found, {"path": path.name, "sha256": digest.hexdigest(), "matched": len(found), "requested": len(wanted)}


def _chain(first: str, rest: io.TextIOBase):
    buffer = first
    for line in rest:
        if buffer:
            yield buffer + line
            buffer = ""
        else:
            yield line
    if buffer:
        yield buffer


# ---------------------------------------------------------------------------------------------
# Live entity lookups — 100 organisation numbers per request
# ---------------------------------------------------------------------------------------------

def fetch_entities(fetcher: Fetcher, orgs: list[str], phase: str = "registry") -> tuple[dict[str, tuple[dict, Snapshot]], list[str]]:
    result: dict[str, tuple[dict, Snapshot]] = {}
    errors: list[str] = []
    for i in range(0, len(orgs), 100):
        chunk = orgs[i:i + 100]
        url = f"{API}/enheter?organisasjonsnummer={','.join(chunk)}&size=100"
        try:
            snap = fetcher.get_json(url, phase=phase, retries=2)
        except BudgetExhausted:
            errors.append("budget")
            break
        if not snap.ok:
            errors.append(f"HTTP {snap.status} {snap.error or ''}")
            continue
        try:
            body = snap.json()
            if not isinstance(body, dict):
                raise ValueError("registry response is not an object")
            rows = _get(body, "_embedded", "enheter") or []
            if not isinstance(rows, list):
                raise ValueError("registry entities are not a list")
            for entity in rows:
                if isinstance(entity, dict) and str(entity.get("organisasjonsnummer")) in chunk:
                    result[str(entity["organisasjonsnummer"])] = (entity, snap)
        except (ValueError, TypeError) as exc:
            errors.append(f"invalid registry response: {type(exc).__name__}")
    return result, errors


def entity_claims(pb: ProfileBuilder, entity: dict[str, Any], *, retrieved_at: str, source_class: str,
                  method: str, source_url: str | None = None, snapshot: Snapshot | None = None) -> None:
    org = pb.org
    if str(entity.get("organisasjonsnummer") or "") != org:
        pb.set_state("identity", "ambiguous", "registry entity key does not match requested organisation")
        return
    url = snapshot.final_url if snapshot else source_url or ENTITY_URL.format(org=org)
    digest = snapshot.sha256 if snapshot else canonical_hash(entity)
    prefix = ""
    if snapshot:
        source_rows = _get(snapshot.json(), "_embedded", "enheter")
        if isinstance(source_rows, list):
            index = next((i for i, row in enumerate(source_rows) if str(row.get("organisasjonsnummer")) == org), None)
            if index is None:
                raise ValueError("identity record absent from source snapshot")
            prefix = f"/_embedded/enheter/{index}"

    def ev(key: str, value: Any, period: dict | None = None) -> str:
        pointer = prefix + "/" + key.replace("~", "~0").replace("/", "~1")
        raw = entity.get(key)
        quote = span(key, value)
        if key == "kommune":
            address_key = "forretningsadresse" if _get(entity, "forretningsadresse", "kommune") else "postadresse"
            pointer = prefix + f"/{address_key}/kommune"
            raw = _get(entity, address_key, "kommune")
        if key == "historiskeNavn" and isinstance(raw, list) and value in raw:
            pointer += "/" + str(raw.index(value))
            raw = value
            quote = json.dumps(value, ensure_ascii=False)
        return pb.add_evidence(Evidence(url, source_class, retrieved_at, digest, quote, f"{method}:{key}", NLOD,
                                        identity_reason="exact organisation-number key", reporting_period=period,
                                        locator={"type": "json_pointer", "pointer": pointer, "value": raw,
                                                 "organisation_number": org, "parent_pointer": prefix + "/organisasjonsnummer"}))

    def add(family: str, field: str, label: str, value: Any, key_name: str, raw: Any = None, **kw: Any) -> None:
        if value in (None, "", []):
            return
        pb.add(Claim(family, field, value, [ev(key_name, raw if raw is not None else value)], label=label, **kw))

    add("identity", "legal_name", "Legal name", entity.get("navn"), "navn")
    form = entity.get("organisasjonsform") or {}
    if form.get("kode"):
        value = f"{form.get('beskrivelse')} ({form['kode']})" if form.get("beskrivelse") else form["kode"]
        add("identity", "legal_form", "Legal form", value, "organisasjonsform", {k: v for k, v in form.items() if k != "_links"})
    add("identity", "founded_date", "Founded", entity.get("stiftelsesdato"), "stiftelsesdato")
    add("identity", "registration_date", "Registered in Enhetsregisteret", entity.get("registreringsdatoEnhetsregisteret"), "registreringsdatoEnhetsregisteret")
    if entity.get("registrertIForetaksregisteret"):
        if entity.get("registreringsdatoForetaksregisteret"):
            add("identity", "business_register_date", "Registered in Foretaksregisteret", entity["registreringsdatoForetaksregisteret"],
                "registreringsdatoForetaksregisteret")
        else:
            add("identity", "business_register_registered", "Registered in Foretaksregisteret", "yes", "registrertIForetaksregisteret", True)
    if entity.get("registrertIMvaregisteret") is not None:
        add("identity", "vat_registered", "VAT registered", "yes" if entity.get("registrertIMvaregisteret") else "no", "registrertIMvaregisteret",
            entity.get("registrertIMvaregisteret"), effective_date=entity.get("registreringsdatoMerverdiavgiftsregisteret"))
    add("identity", "business_address", "Business address", fmt_address(entity.get("forretningsadresse")), "forretningsadresse",
        {k: v for k, v in (entity.get("forretningsadresse") or {}).items()})
    add("identity", "postal_address", "Postal address", fmt_address(entity.get("postadresse")), "postadresse",
        {k: v for k, v in (entity.get("postadresse") or {}).items()})
    municipality = _get(entity, "forretningsadresse", "kommune") or _get(entity, "postadresse", "kommune")
    add("identity", "municipality", "Municipality", municipality.title() if isinstance(municipality, str) else None, "kommune", municipality)
    if entity.get("harRegistrertAntallAnsatte") is not False and entity.get("antallAnsatte") is not None:
        add("identity", "employees", "Registered employees", entity.get("antallAnsatte"), "antallAnsatte",
            effective_date=entity.get("registreringsdatoAntallAnsatteEnhetsregisteret"))
    capital = entity.get("kapital") or {}
    if capital.get("belop") is not None:
        add("identity", "share_capital", f"{capital.get('type') or 'Share capital'}", capital.get("belop"), "kapital", capital,
            unit=capital.get("valuta"), effective_date=capital.get("innfortDato"))
    for item in entity.get("historiskeNavn") or []:
        if item.get("navn"):
            pb.add(Claim("identity", "former_name", item["navn"], [ev("historiskeNavn", item)], label="Former name",
                         key=f"former_name:{item['navn']}", period={"from": str(item.get("fraDato", ""))[:10], "to": str(item.get("tilDato", ""))[:10]}))
    purpose = " ".join(entity.get("vedtektsfestetFormaal") or entity.get("aktivitet") or [])
    if purpose:
        add("identity", "registered_purpose", "Registered business purpose", purpose, "vedtektsfestetFormaal" if entity.get("vedtektsfestetFormaal") else "aktivitet",
            entity.get("vedtektsfestetFormaal") or entity.get("aktivitet"))
    sector = entity.get("institusjonellSektorkode") or {}
    if sector.get("beskrivelse"):
        add("identity", "sector", "Institutional sector", sector["beskrivelse"], "institusjonellSektorkode", sector)
    if entity.get("hjemmeside"):
        add("identity", "registry_declared_website", "Website declared in registry", entity["hjemmeside"], "hjemmeside")
    if entity.get("erIKonsern") is not None:
        add("identity", "part_of_group", "Part of a corporate group (registry flag)", "yes" if entity.get("erIKonsern") else "no", "erIKonsern", entity.get("erIKonsern"))
    if entity.get("telefon") and form.get("kode") not in ("ENK",):
        add("contact", "registry_phone", "Phone (registry)", entity["telefon"], "telefon")

    # status
    flags = {
        "konkurs": "Bankrupt",
        "underAvvikling": "Under liquidation",
        "underTvangsavviklingEllerTvangsopplosning": "Under compulsory liquidation/dissolution",
    }
    active = True
    for key, label in flags.items():
        if entity.get(key):
            active = False
            add("status", key, label, "yes", key, True, effective_date=entity.get(key + "Dato"))
    if entity.get("slettedato"):
        active = False
        add("status", "deleted", "Deleted from registry", entity["slettedato"], "slettedato")
    if all(entity.get(k) is not None for k in flags) or entity.get("konkurs") is not None:
        add("status", "registry_status", "Registry status", "active" if active else "inactive/winding up",
            "konkurs", entity.get("konkurs"))
    if entity.get("sisteInnsendteAarsregnskap"):
        add("identity", "latest_filed_year", "Latest submitted annual accounts (year)", str(entity["sisteInnsendteAarsregnskap"]), "sisteInnsendteAarsregnskap")

    # industry
    for idx in (1, 2, 3):
        code = entity.get(f"naeringskode{idx}") or {}
        if code.get("kode"):
            pb.add(Claim("industry", "industry_code" if idx == 1 else "secondary_industry_code", f"{code['kode']} {code.get('beskrivelse') or ''}".strip(),
                         [ev(f"naeringskode{idx}", code)], label="Primary industry (NACE)" if idx == 1 else "Secondary industry (NACE)",
                         key=f"naeringskode{idx}"))


# ---------------------------------------------------------------------------------------------
# Annual accounts (Regnskapsregisteret)
# ---------------------------------------------------------------------------------------------

FIN_FIELDS = [
    ("revenue", "Total operating revenue", ("resultatregnskapResultat", "driftsresultat", "driftsinntekter", "sumDriftsinntekter")),
    ("sales_revenue", "Sales revenue", ("resultatregnskapResultat", "driftsresultat", "driftsinntekter", "salgsinntekter")),
    ("operating_expenses", "Total operating expenses", ("resultatregnskapResultat", "driftsresultat", "driftskostnad", "sumDriftskostnad")),
    ("operating_result", "Operating result", ("resultatregnskapResultat", "driftsresultat", "driftsresultat")),
    ("net_financial_items", "Net financial items", ("resultatregnskapResultat", "finansresultat", "nettoFinans")),
    ("profit_before_tax", "Profit before tax", ("resultatregnskapResultat", "ordinaertResultatFoerSkattekostnad")),
    ("net_result", "Net result for the year", ("resultatregnskapResultat", "aarsresultat")),
    ("total_assets", "Total assets", ("eiendeler", "sumEiendeler")),
    ("fixed_assets", "Fixed assets", ("eiendeler", "anleggsmidler", "sumAnleggsmidler")),
    ("current_assets", "Current assets", ("eiendeler", "omloepsmidler", "sumOmloepsmidler")),
    ("cash", "Bank deposits and cash", ("eiendeler", "sumBankinnskuddOgKontanter")),
    ("equity", "Total equity", ("egenkapitalGjeld", "egenkapital", "sumEgenkapital")),
    ("total_debt", "Total debt", ("egenkapitalGjeld", "gjeldOversikt", "sumGjeld")),
    ("short_term_debt", "Short-term debt", ("egenkapitalGjeld", "gjeldOversikt", "kortsiktigGjeld", "sumKortsiktigGjeld")),
    ("long_term_debt", "Long-term debt", ("egenkapitalGjeld", "gjeldOversikt", "langsiktigGjeld", "sumLangsiktigGjeld")),
]


def _num(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def accounts_claims(pb: ProfileBuilder, snap: Snapshot) -> None:
    records = snap.json() if snap.ok else []
    if not isinstance(records, list) or not records:
        pb.set_state("financials", "not_available", "Regnskapsregisteret returned no annual-account records", snap.url)
        return
    url = snap.url
    for record_index, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        owner = rec.get("organisasjonsnummer") or _get(rec, "virksomhet", "organisasjonsnummer")
        if owner and str(owner) != pb.org:
            pb.candidates.append({"family": "financials", "decision": "rejected", "reason": "account record has a different organisation number"})
            continue
        period = rec.get("regnskapsperiode") or {}
        p = {"from": period.get("fraDato"), "to": period.get("tilDato")}
        account_type = (rec.get("regnskapstype") or "SELSKAP").upper()
        currency = rec.get("valuta") or None
        scope = "company" if account_type == "SELSKAP" else "group (consolidated)"
        for field, label, path in FIN_FIELDS:
            value = _get(rec, *path)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                continue  # missing stays missing — never zero
            value = _num(value)
            ev = pb.add_evidence(Evidence(url, "official_registry", snap.retrieved_at, snap.sha256, span(path[-1], value),
                                          f"regnskapsregisteret_api:{'.'.join(path)}", NLOD, identity_reason="exact organisation-number key",
                                          reporting_period=p, locator={"type": "json_pointer", "pointer": f"/{record_index}/" + "/".join(path),
                                                                       "value": value, "record_pointer": f"/{record_index}", "organisation_number": pb.org,
                                                                       "currency": currency, "period": p}))
            pb.add(Claim("financials", field, value, [ev], label=f"{label} ({scope})", period=p, unit=currency,
                         key=f"{field}:{account_type}:{p['to']}", note=f"account_type={account_type}"))
        audit = rec.get("revisjon") or {}
        if audit:
            audited = "not audited" if audit.get("ikkeRevidertAarsregnskap") or audit.get("fravalgRevisjon") else "audited"
            ev = pb.add_evidence(Evidence(url, "official_registry", snap.retrieved_at, snap.sha256, span("revisjon", audit),
                                          "regnskapsregisteret_api:revisjon", NLOD, reporting_period=p))
            pb.add(Claim("financials", "audit_status", audited, [ev], label=f"Audit status ({scope})", period=p, key=f"audit:{account_type}:{p['to']}"))
        rules = _get(rec, "regnkapsprinsipper", "regnskapsregler")
        if rules:
            ev = pb.add_evidence(Evidence(url, "official_registry", snap.retrieved_at, snap.sha256, span("regnskapsregler", rules),
                                          "regnskapsregisteret_api:regnkapsprinsipper", NLOD, reporting_period=p))
            pb.add(Claim("financials", "accounting_rules", rules, [ev], label=f"Accounting rules ({scope})", period=p, key=f"rules:{account_type}:{p['to']}"))
    pb.set_state("financials", "available", "official annual accounts", url)


def history_claims(pb: ProfileBuilder, snap: Snapshot) -> None:
    """Official filing history: every year with a filed annual-account copy, linked to the official copy (PDF)."""
    years = sorted({str(y) for y in (snap.json() if snap.ok else []) if str(y).isdigit()}, reverse=True)
    for year in years[:20]:
        ev = pb.add_evidence(Evidence(snap.url, "official_registry", snap.retrieved_at, snap.sha256, snap.text()[:600],
                                      "regnskapsregisteret_kopi_api:aar", NLOD, identity_reason="exact organisation-number key",
                                      reporting_period={"from": f"{year}-01-01", "to": f"{year}-12-31"}))
        pb.add(Claim("financials", "filed_annual_accounts", {"year": year, "official_copy": HISTORY_PDF.format(org=pb.org, year=year)}, [ev],
                     label="Annual accounts filed (official copy)", key=f"filing:{year}", period={"from": f"{year}-01-01", "to": f"{year}-12-31"}))


# ---------------------------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------------------------

ROLE_FIELDS = {
    "DAGL": "ceo", "LEDE": "board_chair", "NEST": "deputy_chair", "MEDL": "board_member", "VARA": "deputy_board_member",
    "REVI": "auditor", "REGN": "accountant", "KONT": "contact_person", "INNH": "owner", "DTPR": "partner", "DTSO": "partner",
    "KOMP": "general_partner", "BEST": "managing_shipowner", "FFØR": "business_manager", "OBS": "observer", "STYR": "board_member",
    "SAM": "co_owner", "KDEB": "estate_administrator", "PROK": "procuration", "SIGN": "signature_right", "EIKM": "owner_municipality",
}


def roles_claims(pb: ProfileBuilder, snap: Snapshot) -> None:
    body = snap.json() if snap.ok else {}
    if isinstance(body, dict):
        declared = body.get("organisasjonsnummer")
        href = _get(body, "_links", "self", "href")
        if (declared and str(declared) != pb.org) or (href and f"/enheter/{pb.org}/roller" not in href):
            pb.set_state("leadership", "ambiguous", "role response belongs to a different organisation", snap.url)
            return
    groups = body.get("rollegrupper") if isinstance(body, dict) else None
    if not groups:
        pb.set_state("leadership", "not_available", "no public roles registered", snap.url)
        return
    count = 0
    for group_index, group in enumerate(groups):
        changed = group.get("sistEndret")
        for role_index, item in enumerate(group.get("roller") or []):
            if item.get("avregistrert") or item.get("fratraadt"):
                continue
            person = item.get("person") or {}
            if person.get("erDoed"):
                continue
            code = _get(item, "type", "kode") or ""
            desc = _get(item, "type", "beskrivelse") or code
            name_parts = person.get("navn") or {}
            name = " ".join(x for x in [name_parts.get("fornavn"), name_parts.get("mellomnavn"), name_parts.get("etternavn")] if x)
            entity = item.get("enhet") or {}
            holder_org = entity.get("organisasjonsnummer")
            if not name:
                names = entity.get("navn")
                name = " ".join(names) if isinstance(names, list) else (names or "")
            if not name:
                continue
            value = f"{name} (org. {holder_org})" if holder_org else name
            name_span = span("navn", name_parts) if name_parts else span("navn", entity.get("navn"))
            ev = pb.add_evidence(Evidence(snap.url, "official_registry", snap.retrieved_at, snap.sha256, name_span,
                                          "brreg_roller_api:rollegrupper.roller", NLOD, identity_reason="exact organisation-number key",
                                          locator={"type": "json_pointer", "pointer": f"/rollegrupper/{group_index}/roller/{role_index}/" + ("person/navn" if name_parts else "enhet/navn"),
                                                   "value": name_parts if name_parts else entity.get("navn"), "organisation_number": pb.org, "role_code": code}))
            field = ROLE_FIELDS.get(code, "role_" + code.lower())
            pb.add(Claim("leadership", field, value, [ev], label=desc, effective_date=changed, key=f"role:{code}:{name}"))
            count += 1
    pb.set_state("leadership", "available" if count else "not_available", f"{count} active roles" if count else "no active roles", snap.url)


# ---------------------------------------------------------------------------------------------
# Registered workplaces (underenheter)
# ---------------------------------------------------------------------------------------------

def subunit_claims(pb: ProfileBuilder, snap: Snapshot) -> None:
    body = snap.json() if snap.ok else {}
    units = _get(body, "_embedded", "underenheter") or []
    if len(units) > 200 or int((_get(body, "page", "totalPages") or 1)) > 1:
        pb.extra.setdefault("incomplete_families", {})["locations"] = "workplace inventory truncated; absence cannot establish closure"
    if not units:
        pb.set_state("locations", "not_available", "no registered sub-units (workplaces)", snap.url)
        return
    for unit_index, unit in enumerate(units[:200]):
        if str(unit.get("overordnetEnhet") or "") != pb.org:
            continue
        if unit.get("nedleggelsesdato") or unit.get("slettedato"):
            continue
        cands = pb.extra.setdefault("site_candidates", [])
        if unit.get("hjemmeside"):
            cands.append((unit["hjemmeside"], "subunit_declared"))
        if unit.get("epostadresse") and "@" in unit["epostadresse"]:
            pb.extra.setdefault("emails", []).append(unit["epostadresse"].lower())
            cands.append((unit["epostadresse"].split("@", 1)[1], "subunit_email_domain"))
        org = unit.get("organisasjonsnummer")
        addr = fmt_address(unit.get("beliggenhetsadresse") or unit.get("postadresse"))
        value = {
            "name": unit.get("navn"),
            "organisation_number": org,
            "address": addr,
            "municipality": (_get(unit, "beliggenhetsadresse", "kommune") or "").title() or None,
            "employees": unit.get("antallAnsatte") if unit.get("harRegistrertAntallAnsatte") is not False else None,
            "industry": " ".join(x for x in [_get(unit, "naeringskode1", "kode"), _get(unit, "naeringskode1", "beskrivelse")] if x) or None,
            "opened": unit.get("oppstartsdato"),
        }
        value = {k: v for k, v in value.items() if v not in (None, "")}
        ev = pb.add_evidence(Evidence(snap.final_url, "official_registry", snap.retrieved_at,
                                      snap.sha256, span("organisasjonsnummer", org),
                                      "brreg_underenheter_api:overordnetEnhet", NLOD, identity_reason="sub-unit registered under this organisation number (overordnetEnhet)",
                                      locator={"type": "json_pointer", "pointer": f"/_embedded/underenheter/{unit_index}/organisasjonsnummer", "value": org,
                                               "parent_pointer": f"/_embedded/underenheter/{unit_index}/overordnetEnhet", "organisation_number": pb.org}))
        pb.add(Claim("locations", "workplace", value, [ev], label="Registered workplace", key=f"workplace:{org}", effective_date=unit.get("oppstartsdato")))
    pb.set_state("locations", "available", f"{len(units)} registered sub-units", snap.url)


# ---------------------------------------------------------------------------------------------
# Group structure (labelled relationships, never merged)
# ---------------------------------------------------------------------------------------------

def group_claims(pb: ProfileBuilder, snap: Snapshot) -> None:
    if not snap.ok:
        pb.set_state("group", "not_available", "no group structure returned", snap.url)
        return
    body = snap.json()
    found = 0

    def walk(node: dict, depth: int = 0) -> None:
        nonlocal found
        for child in node.get("children") or []:
            org = child.get("organisasjonsnummer")
            parent = child.get("parentOrganisasjonsnummer")
            relation = _get(child, "knytningsform", "beskrivelse") or "group relation"
            if org == pb.org and parent:
                ev = pb.add_evidence(Evidence(snap.url, "official_registry", snap.retrieved_at, snap.sha256,
                                              json.dumps({k: child.get(k) for k in ("parentNavn", "parentOrganisasjonsnummer", "knytningsform", "grunnlag")}, ensure_ascii=False),
                                              "brreg_konsernstruktur_api", NLOD))
                pb.add(Claim("group", "parent_company", {"name": child.get("parentNavn"), "organisation_number": parent, "relation": relation, "share": child.get("grunnlag")},
                             [ev], label="Parent company (labelled relation, not merged)", key=f"parent:{parent}", effective_date=child.get("dato")))
                found += 1
            elif parent == pb.org and found < 60:
                ev = pb.add_evidence(Evidence(snap.url, "official_registry", snap.retrieved_at, snap.sha256,
                                              json.dumps({k: child.get(k) for k in ("navn", "organisasjonsnummer", "knytningsform", "grunnlag")}, ensure_ascii=False),
                                              "brreg_konsernstruktur_api", NLOD))
                pb.add(Claim("group", "subsidiary", {"name": child.get("navn"), "organisation_number": org, "relation": relation, "share": child.get("grunnlag")},
                             [ev], label="Subsidiary (labelled relation, not merged)", key=f"subsidiary:{org}", effective_date=child.get("dato")))
                found += 1
            walk(child, depth + 1)

    if isinstance(body, dict):
        walk(body)
        if body.get("organisasjonsnummer") == pb.org and body.get("parentOrganisasjonsnummer"):
            walk({"children": [body]})
    pb.set_state("group", "available" if found else "not_available", "official group structure" if found else "no group links returned", snap.url)


# ---------------------------------------------------------------------------------------------
# Dated official activity: registry change log (batched, JSON-patch level changes)
# ---------------------------------------------------------------------------------------------

CHANGE_LABELS = {
    "navn": "Legal name changed",
    "forretningsadresse": "Business address changed",
    "postadresse": "Postal address changed",
    "antallAnsatte": "Registered employee count updated",
    "naeringskode1": "Primary industry code changed",
    "hjemmeside": "Registry website changed",
    "konkurs": "Bankruptcy status changed",
    "underAvvikling": "Liquidation status changed",
    "underTvangsavviklingEllerTvangsopplosning": "Compulsory dissolution status changed",
    "organisasjonsform": "Legal form changed",
    "kapital": "Share capital changed",
    "vedtektsfestetFormaal": "Registered purpose changed",
    "registrertIMvaregisteret": "VAT registration changed",
    "registrertIForetaksregisteret": "Business-register registration changed",
    "vedtektsdato": "Articles of association updated",
    "sisteInnsendteAarsregnskap": "New annual accounts submitted",
    "telefon": "Registry phone changed",
    "epostadresse": "Registry e-mail changed",
}
SKIP_CHANGE = {"registreringsdatoAntallAnsatteEnhetsregisteret", "registreringsdatoAntallAnsatteNAVAaregisteret", "harRegistrertAntallAnsatte"}


def _describe(changes: list[dict]) -> tuple[str, list[dict]] | None:
    labels: list[str] = []
    detail: list[dict] = []
    for change in changes or []:
        path = str(change.get("path", "")).strip("/").split("/")
        root = path[0] if path else ""
        if root in SKIP_CHANGE or not root:
            continue
        label = CHANGE_LABELS.get(root)
        if not label:
            continue
        if label not in labels:
            labels.append(label)
        detail.append({"op": change.get("op"), "path": change.get("path"), "value": change.get("value")})
    if not labels:
        return None
    return "; ".join(labels), detail


def fetch_activity(fetcher: Fetcher, orgs: list[str], *, days: int = 730, phase: str = "activity") -> tuple[dict[str, list[tuple[dict, Snapshot]]], dict[str, list[tuple[dict, Snapshot]]], list[str]]:
    since_dt = datetime.now(timezone.utc) - timedelta(days=days)
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    entity_events: dict[str, list[tuple[dict, Snapshot]]] = {}
    role_events: dict[str, list[tuple[dict, Snapshot]]] = {}
    errors: list[str] = []
    for i in range(0, len(orgs), 100):
        chunk = ",".join(orgs[i:i + 100])
        try:
            page = 0
            while True:
                snap = fetcher.get_json(ENTITY_UPDATES_URL.format(orgs=chunk, since=since, size=2000) + f"&page={page}", phase=phase, retries=1, timeout=60)
                if not snap.ok:
                    errors.append(f"entity updates HTTP {snap.status}")
                    break
                body = snap.json()
                if not isinstance(body, dict) or not isinstance(body.get("_embedded", {}), dict) or "enheter" in body.get("_embedded", {}):
                    raise ValueError("unexpected activity response schema")
                for item in _get(body, "_embedded", "oppdaterteEnheter") or []:
                    entity_events.setdefault(str(item.get("organisasjonsnummer")), []).append((item, snap))
                info = body.get("page") or {}
                page += 1
                if page >= int(info.get("totalPages") or 0) or (page + 1) * 2000 > 10000:
                    break
            snap = fetcher.get_json(ROLE_UPDATES_URL.format(orgs=chunk, since=since, size=5000), phase=phase, retries=1, timeout=60)
            if snap.ok:
                body = snap.json()
                if not isinstance(body, list):
                    raise ValueError("unexpected role updates response schema")
                for item in body if isinstance(body, list) else []:
                    org = str(_get(item, "data", "organisasjonsnummer"))
                    role_events.setdefault(org, []).append((item, snap))
            else:
                errors.append(f"role updates HTTP {snap.status}")
        except BudgetExhausted:
            errors.append("budget")
            break
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            errors.append(f"invalid activity response: {type(exc).__name__}")
    return entity_events, role_events, errors


def activity_claims(pb: ProfileBuilder, entity_events: list[tuple[dict, Snapshot]], role_events: list[tuple[dict, Snapshot]], max_events: int = 25) -> int:
    added = 0
    rows: list[tuple[str, str, dict, Snapshot, str]] = []
    for item, snap in entity_events:
        kind = item.get("endringstype")
        if kind == "Ny":
            rows.append((item.get("dato", ""), "Registered in Enhetsregisteret", {"endringstype": kind}, snap, str(item.get("oppdateringsid"))))
            continue
        described = _describe(item.get("endringer") or [])
        if described:
            label, field_changes = described
            rows.append((item.get("dato", ""), label, {"endringstype": kind, "endringer": field_changes}, snap, str(item.get("oppdateringsid"))))
    seen_role_days: set[str] = set()
    for item, snap in role_events:
        day = str(item.get("time", ""))[:10]
        if day in seen_role_days:
            continue
        seen_role_days.add(day)
        rows.append((item.get("time", ""), "Roles (board/management) updated in registry", {"type": item.get("type"), "id": item.get("id")}, snap, "role:" + str(item.get("id"))))
    rows.sort(key=lambda r: r[0], reverse=True)
    for when, label, detail, snap, uid in rows[:max_events]:
        day = str(when)[:10]
        link = snap.url.split("?")[0] + f"?organisasjonsnummer={pb.org}" + (f"&dato={day}T00:00:00.000Z&includeChanges=true&size=100" if "oppdateringer/enheter" in snap.url
                                                                           else f"&afterTime={day}T00:00:00.000Z&size=100")
        ev = pb.add_evidence(Evidence(snap.final_url, "official_registry", snap.retrieved_at,
                                      snap.sha256, span("time" if uid.startswith("role:") else "dato", when),
                                      "brreg_oppdateringer_api", NLOD, identity_reason="exact organisation-number key"))
        pb.add(Claim("activity", "registry_event", label, [ev], label="Official registry event", effective_date=str(when)[:10], key=f"event:{uid}",
                     note=json.dumps(detail.get("endringer"), ensure_ascii=False)[:300] if detail.get("endringer") else None))
        added += 1
    return added
