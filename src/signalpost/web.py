"""Official-website discovery behind a strict exact-entity identity gate, plus company-owned extraction.

Publication rule: a domain is the company's official website only with one of these proofs
  1. orgnr_on_site      — the company's exact organisation number (mod-11 valid) is printed on the site
                          and the site does not present a *different* organisation number as its owner;
  2. contact_match      — every distinctive legal-name token is on the site AND the registry phone number
                          or the registry street address + postcode is on the site (no conflicting orgnr);
  3. registry_declared  — the registry itself lists this website for the entity AND all distinctive
                          legal-name tokens appear in the site's identity fields (title / site name / JSON-LD),
                          with no conflicting organisation number.
Everything else is `ambiguous` (kept as an audit candidate, never published). Parent / brand / sister
sites (a different orgnr) are rejected as `related_site`. Social links, e-mail, description and news
are only taken from a site that passed the gate.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from lxml import etree, html as lhtml

from .budget import BudgetExhausted
from .http import Fetcher, Snapshot, host_is_public
from .job_dates import job_expired, job_not_yet_published, parse_job_date
from .model import Claim, Evidence, ProfileBuilder

# Who declared a candidate website, worded exactly (the identity reason must name the real source).
DECLARED_BY = {
    "registry_declared": "the registry (Enhetsregisteret) declares this website",
    "subunit_declared": "the registry declares this website for one of the company's registered workplaces",
    "wikidata_p856": "the Wikidata item carrying this organisation number (P2333) lists this website (P856)",
}
FREE_MAIL = {
    "gmail.com", "hotmail.com", "hotmail.no", "outlook.com", "outlook.no", "live.com", "live.no", "yahoo.com", "yahoo.no",
    "online.no", "icloud.com", "me.com", "msn.com", "start.no", "frisurf.no", "broadpark.no", "getmail.no", "c2i.net",
    "lyse.net", "altibox.no", "telia.no", "netcom.no", "hotmail.co.uk", "aol.com", "mail.com", "protonmail.com", "proton.me",
    "gmx.com", "gmx.net", "ebnett.no", "tele2.no", "chello.no", "bluezone.no", "tdcadsl.no", "loqal.no", "monet.no",
    "sensewave.com", "haugnett.no", "enivest.net", "nktv.no", "vikenfiber.no", "tussa.com", "vtel.no", "neasonline.no",
}
# Host families that are never "the company's website"
NON_COMPANY_HOSTS = (
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "youtube.com", "tiktok.com", "google.com",
    "proff.no", "gulesider.no", "1881.no", "purehelp.no", "brreg.no", "finn.no", "mittanbud.no", "bedriftsdatabasen.no",
    "firmasok.no", "regnskapstall.no", "kompass.com", "enirodigital", "wix.com", "wixsite.com", "squarespace.com",
    "weebly.com", "blogspot.com", "wordpress.com", "123hjemmeside.no", "jimdo.com", "jimdofree.com", "business.site",
    "nav.no", "altinn.no", "vipps.no", "linktr.ee", "godaddysites.com", "one.com", "domeneshop.no", "uniweb.no",
)
PARKED_MARKERS = (
    "domain is for sale", "domain for sale", "domenet er til salgs", "dette domenet er til salgs", "kjøp dette domenet",
    "hugedomains", "parked at", "parked domain", "this domain is parked", "domeneshop.no/parkert", "parkert hos",
    "her flytter snart en ny gjest", "under construction", "under konstruksjon", "kommer snart", "coming soon",
    "website is under construction", "nettsiden er under utvikling", "default web site page", "welcome to nginx",
    "apache2 default page", "it works!", "index of /", "account suspended", "this account has been suspended",
    "just another wordpress site", "bare nok en wordpress-side", "en ny wordpress-side", "web hosting by", "sedo",
    "this site can’t be reached", "future home of", "registered at one.com", "domenet er registrert",
)
GENERIC_TOKENS = {
    "norge", "norway", "norsk", "norske", "nordic", "scandinavia", "group", "gruppen", "holding", "holdings", "invest",
    "investering", "eiendom", "eiendommer", "property", "properties", "service", "services", "consult", "consulting",
    "konsult", "bygg", "byggservice", "entreprenor", "transport", "regnskap", "regnskapskontor", "handel", "drift",
    "utvikling", "management", "partner", "partners", "solutions", "systems", "teknikk", "tjenester", "kompani", "co",
    "company", "the", "og", "and", "i", "pa", "av", "for", "til", "med", "nye", "ny", "maler", "elektro", "ror",
    "vvs", "auto", "bil", "data", "it", "media", "design", "studio", "sport", "helse", "klinikk", "tannlege", "frisor",
    "eiendomsselskap", "capital", "ventures", "international", "int", "nord", "sor", "vest", "ost", "midt",
}
HOLDING_WORDS = {"holding", "holdings", "invest", "investering", "investment", "investments", "capital", "eiendom", "eiendommer",
                 "property", "properties", "forvaltning", "ventures", "finans", "kapital", "eie", "beholdning"}
LEGAL = {"as", "asa", "ans", "da", "sa", "ba", "nuf", "enk", "iks", "kf", "stiftelsen", "sf", "ks", "bbl", "brl", "ltd", "ab", "inc", "llc", "gmbh"}
SOCIAL_PATTERNS = {
    "linkedin": re.compile(r"^https?://([a-z]{2,3}\.)?linkedin\.com/(company|school|showcase)/[^/?#]+", re.I),
    "facebook": re.compile(r"^https?://(www\.|m\.|nb-no\.)?facebook\.com/(?!sharer|share|dialog|plugins|tr\b|groups/|events/|hashtag/|login|policy|privacy)[^/?#]+", re.I),
    "instagram": re.compile(r"^https?://(www\.)?instagram\.com/(?!p/|explore|accounts|reel/)[^/?#]+", re.I),
    "youtube": re.compile(r"^https?://(www\.)?youtube\.com/(channel/|c/|user/|@)[^/?#]+", re.I),
    "x_twitter": re.compile(r"^https?://(www\.)?(twitter|x)\.com/(?!intent|share|home|search|hashtag)[^/?#]+", re.I),
    "tiktok": re.compile(r"^https?://(www\.)?tiktok\.com/@[^/?#]+", re.I),
}
ROLE_MAILBOXES = {
    "post", "postmottak", "info", "kontakt", "contact", "firmapost", "mail", "salg", "sales", "office", "kontor", "kundeservice",
    "support", "service", "hei", "hello", "hallo", "booking", "bestilling", "ordre", "order", "faktura", "invoice", "regnskap",
    "admin", "resepsjon", "reception", "jobb", "karriere", "career", "careers", "jobs", "press", "presse", "media", "marketing",
    "marked", "butikk", "shop", "nettbutikk", "web", "verksted", "drift", "bedrift", "kunde", "kunder", "enquiries", "inquiries",
}
SUBPAGE_HINTS = re.compile(r"(kontakt|contact|om-oss|om_oss|omoss|about|personvern|privacy|vilkar|vilkår|terms|impressum|kjopsbetingelser|salgsbetingelser|firma|selskapet|company)", re.I)
NEWS_HINTS = re.compile(r"(nyheter|aktuelt|news|blogg|blog|presse|press|artikler|articles|siste-nytt|innsikt|borsmelding|børsmelding|investor)", re.I)
ORG_RE = re.compile(r"(?<![\d])(\d{3})[\s .\-]?(\d{3})[\s .\-]?(\d{3})(?![\d])")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def fold(text: str | None) -> str:
    text = (text or "").casefold().translate(str.maketrans({"ø": "o", "å": "a", "æ": "ae", "ö": "o", "ä": "a", "ü": "u"}))
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def name_tokens(name: str | None) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", fold(name)) if t not in LEGAL]


def distinctive_tokens(name: str | None) -> list[str]:
    return [t for t in name_tokens(name) if t not in GENERIC_TOKENS and len(t) >= 3 and not t.isdigit()]


def valid_orgnr(org: str) -> bool:
    if len(org) != 9 or not org.isdigit() or org[0] not in "89":
        return False
    weights = [3, 2, 7, 6, 5, 4, 3, 2]
    remainder = sum(int(d) * w for d, w in zip(org[:8], weights)) % 11
    check = 0 if remainder == 0 else 11 - remainder
    return check != 10 and check == int(org[8])


def find_orgnrs(text: str) -> set[str]:
    found = set()
    for match in ORG_RE.finditer(text):
        candidate = "".join(match.groups())
        if valid_orgnr(candidate):
            # require an org-number context nearby to avoid matching random 9-digit numbers (phones are 8 digits)
            window = fold(text[max(0, match.start() - 40): match.end() + 10])
            if re.search(r"org|foretaks|mva|vat|reg\.?\s?nr|bedrifts|company|identifier|taxid", window):
                found.add(candidate)
    return found


def registrable_domain(url_or_host: str) -> str:
    host = urllib.parse.urlsplit(url_or_host if "://" in url_or_host else "http://" + url_or_host).hostname or ""
    host = host.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def normalize_site(value: str | None) -> str | None:
    value = (value or "").strip().strip("/")
    if not value or " " in value or "@" in value:
        return None
    if "://" not in value:
        value = "https://" + value
    try:
        parts = urllib.parse.urlsplit(value)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or port not in (None, 80, 443) or not parts.hostname or "." not in parts.hostname:
        return None
    host = parts.hostname.lower()
    if any(host == h or host.endswith("." + h) for h in NON_COMPANY_HOSTS):
        return None
    return urllib.parse.urlunsplit((parts.scheme, host, parts.path or "/", parts.query, ""))


# ------------------------------------------------------------------------------------------ parsing

class Page:
    def __init__(self, snap: Snapshot):
        self.snap = snap
        self.url = snap.final_url
        raw = snap.text()
        self.raw = raw
        try:
            self.doc = lhtml.fromstring(raw) if raw.strip() else None
        except (etree.ParserError, ValueError):
            self.doc = None
        self.title = ""
        self.meta: dict[str, str] = {}
        self.text = ""
        self.links: list[tuple[str, str]] = []
        self.jsonld: list[dict] = []
        self.jsonld_raw: dict[int, str] = {}
        self.identity_nodes: list[dict] = []
        self.feeds: list[str] = []
        if self.doc is None:
            return
        doc = self.doc
        t = doc.find(".//title")
        self.title = " ".join((t.text_content() if t is not None else "").split())
        for m in doc.iter("meta"):
            key = (m.get("property") or m.get("name") or "").lower()
            if key and m.get("content"):
                self.meta.setdefault(key, " ".join(m.get("content").split()))
        for s in doc.xpath("//script[@type='application/ld+json']"):
            try:
                data = json.loads(s.text_content().strip() or "null")
            except (json.JSONDecodeError, ValueError):
                continue
            stack = [(data, True)]
            while stack:
                node, identity_node = stack.pop()
                if isinstance(node, list):
                    stack.extend((v, identity_node) for v in node)
                elif isinstance(node, dict):
                    self.jsonld.append(node)
                    self.jsonld_raw[id(node)] = s.text_content().strip()
                    if identity_node:
                        self.identity_nodes.append(node)
                    stack.extend((v, k == "@graph" and identity_node) for k, v in node.items() if isinstance(v, (dict, list)))
        for link in doc.xpath("//link[@rel='alternate'][@href]"):
            if "rss" in (link.get("type") or "") or "atom" in (link.get("type") or ""):
                self.feeds.append(urllib.parse.urljoin(self.url, link.get("href")))
        for a in doc.xpath("//a[@href]"):
            href = a.get("href", "").strip()
            if href.startswith(("javascript:", "#")):
                continue
            self.links.append((urllib.parse.urljoin(self.url, href), " ".join(a.text_content().split())[:80]))
        for bad in doc.xpath("//script|//style|//noscript|//template"):
            bad.drop_tree() if bad.getparent() is not None else None
        try:
            self.text = " ".join(doc.text_content().split())
        except ValueError:
            self.text = ""

    def identity_values(self) -> list[str]:
        parts = [self.title, self.meta.get("og:site_name", ""), self.meta.get("og:title", ""), self.meta.get("application-name", "")]
        for node in self.identity_nodes:
            if str(node.get("@type", "")).lower() in {"organization", "localbusiness", "corporation", "website", "store", "restaurant", "professionalservice"} or "Organization" in str(node.get("@type", "")):
                for key in ("name", "legalName", "alternateName"):
                    if isinstance(node.get(key), str):
                        parts.append(node[key])
        return [p for p in parts if p]

    def identity_quote(self, legal_name: str, *, allow_title: bool = True) -> str:
        # Titles can name customers, subsidiaries, or an entirely different
        # company ending in the same legal name. Require a whole identity value.
        expected = re.findall(r"[a-z0-9]+", fold(legal_name))
        owners = [self.meta.get("og:site_name"), self.meta.get("application-name")]
        for node in self.identity_nodes:
            if schema_types(node) & {"Organization", "LocalBusiness", "Corporation", "WebSite"}:
                owners.append(node.get("legalName") or node.get("name"))
        owners = [value for value in owners if isinstance(value, str) and value.strip()]
        # A page subject or one company in a portfolio cannot override operator metadata.
        if any(re.findall(r"[a-z0-9]+", fold(value)) != expected for value in owners):
            return ""
        for value in owners or ([self.title] if allow_title else []):
            if expected and re.findall(r"[a-z0-9]+", fold(value)) == expected:
                return value
        return ""

    def identity_fields(self, strict: bool = False) -> str:
        parts = self.identity_values()
        if self.doc is not None and not strict:
            for el in self.doc.xpath("//h1|//header//img[@alt]|//footer"):
                parts.append(el.get("alt") if el.tag == "img" else el.text_content()[:400])
        return " ".join(p for p in parts if p)


# ------------------------------------------------------------------------------------------ gate

def _tokens_present(tokens: list[str], text: str) -> bool:
    words = set(re.findall(r"[a-z0-9]+", fold(text)))
    compact = re.sub(r"[^a-z0-9]", "", fold(text))
    return all(t in words or (len(t) >= 5 and t in compact) for t in tokens)


def exact_name_present(name: str, text: str) -> bool:
    """Match the legal name, including its legal form, never just a shared brand."""
    tokens = re.findall(r"[a-z0-9]+", fold(name))
    words = re.findall(r"[a-z0-9]+", fold(text))
    group_words = {"group", "gruppen", "konsern", "holding", "holdings"}
    if (set(words) & group_words) - set(tokens):
        return False
    qualifiers = HOLDING_WORDS | {"group", "gruppen", "konsern", "norge", "norway", "international"}
    legal_words = re.findall(r"[a-z0-9]+", fold(name))
    legal_form = legal_words[-1] if legal_words and legal_words[-1] in LEGAL else None
    if not tokens:
        return False
    for start in range(len(words) - len(tokens) + 1):
        end = start + len(tokens)
        if words[start:end] != tokens:
            continue
        following = words[end] if end < len(words) else None
        if following not in qualifiers and (following not in LEGAL or following == legal_form):
            return True
    return False


def schema_types(node: dict) -> set[str]:
    value = node.get("@type", [])
    return {v.rsplit("/", 1)[-1] for v in (value if isinstance(value, list) else [value]) if isinstance(v, str)}


def item_url(value: object, base: str) -> str | None:
    """Resolve an item link without accepting script URLs, credentials or malformed ports."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        p = urllib.parse.urlsplit(urllib.parse.urljoin(base, value.strip()))
        if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password or p.port not in (None, 80, 443):
            return None
        path = urllib.parse.quote(p.path or "/", safe="/%:@!$&'()*+,;=")
        path = re.sub(r"%[0-9a-fA-F]{2}", lambda match: match.group().upper(), path)
        return urllib.parse.urlunsplit((p.scheme, p.netloc.lower(), path, p.query, ""))
    except ValueError:
        return None


def single_item_url(url: str, family: str) -> bool:
    p = urllib.parse.urlsplit(url)
    parts = [fold(x) for x in p.path.strip("/").split("/") if x]
    landing = {"news", "nyheter", "aktuelt", "blog", "blogg", "presse", "press", "articles", "artikler", "innsikt",
               "newsroom", "presserom", "press-releases", "press-releases-and-news", "investor", "investors", "borsmelding"}
    if family == "jobs":
        landing = {"careers", "career", "jobs", "job", "jobb", "karriere", "stillinger", "ledige-stillinger", "vacancies", "ledige-jobber",
                   "current-vacancies", "join-us", "work-with-us", "job-search", "open-positions", "opportunities"}
    return bool(parts) and parts[-1] not in landing | {"search", "sok", "index.html", "index.php"} and not any(x in {"search", "sok", "category", "tag"} for x in parts)


def article_page(page: Page) -> bool:
    """CMS publication metadata alone does not turn a utility page into a post."""
    if page.doc is None:
        return False
    parts = {fold(p) for p in urllib.parse.urlsplit(page.url).path.strip("/").split("/")}
    utility = {"contact", "contact-us", "kontakt", "kontakt-oss", "about", "about-us", "om-oss",
               "careers", "career", "jobs", "job", "karriere", "jobb", "stillinger", "ledige-stillinger",
               "privacy", "privacy-policy", "personvern", "terms", "search", "sok", "products", "produkter",
               "services", "tjenester", "shop", "butikk", "hvem-er-vi", "jobbe-hos-oss", "jobb-hos-oss", "work-with-us"}
    if any(schema_types(n) & {"Product", "JobPosting", "ContactPage", "AboutPage", "CollectionPage", "SearchResultsPage"}
           for n in page.identity_nodes):
        return False
    heads = page.doc.xpath("//main//h1|//article//h1|//h1")
    heading = fold(" ".join(heads[0].text_content().split())) if heads else fold(page.title)
    if parts & utility or heading in {p.replace("-", " ") for p in utility} | {"ledige jobber", "vacancies", "our vacancies"}:
        return False
    prose = page.doc.xpath("//p[ancestor::article or ancestor::main]//text()[not(ancestor::nav or ancestor::footer or ancestor::aside)]")
    nodes = [n for n in page.jsonld if schema_types(n) & {"Article", "NewsArticle", "BlogPosting"}]
    bodies = [" ".join(prose)] + [n["articleBody"] for n in nodes if isinstance(n.get("articleBody"), str)]
    # Require real prose. Headings, dates, navigation and a generic Article node
    # by themselves are not a substantive post.
    context = bool(nodes or page.doc.xpath("//article") or parts & {"news", "nyheter", "aktuelt", "blog", "blogg", "presse", "borsmelding", "press-releases"})
    return context and any(len(" ".join(body.split())) >= 80 for body in bodies)


def page_attributed(page: Page, org: str, legal_name: str) -> bool:
    numbers = find_orgnrs(page.text)
    if numbers - {org}:
        return False
    if page.identity_quote(legal_name):
        return True
    if org not in numbers:
        return False
    context = _span_around(page.text, org_pattern(org), width=220)
    if re.search(r"(?:website by|webdesign by|developed by|laget av|designet av).{0,120}" + org_pattern(org), fold(context)):
        return False
    footer = find_orgnrs(_footer_text(page)) if page.doc is not None and page.doc.xpath("//footer") else set()
    invoicing = exact_name_present(legal_name, context) and re.search(
        r"send.{0,40}faktura|faktura.{0,25}(ehf|adresse)|selger|ansvarlig for", fold(context))
    return footer == {org} or bool(invoicing)


def in_verified_scope(page: Page, visit: "SiteVisit", org: str, legal_name: str) -> bool:
    home = visit.pages[0]
    a, b = urllib.parse.urlsplit(home.url), urllib.parse.urlsplit(page.url)
    if a.hostname != b.hostname or find_orgnrs(page.text) - {org}:
        return False
    if visit.address_entity is not None:
        return bool(address_owner(page, org, legal_name, visit.address_entity))
    if page_attributed(page, org, legal_name):
        return True
    # Inheritance requires ownership on the homepage itself, not a subsidiary
    # mention discovered on an unrelated corporate contact page.
    path = a.path.rstrip("/") or "/"
    return page_attributed(home, org, legal_name) and (path == "/" or b.path == path or b.path.startswith(path + "/"))


def contact_proof(entity: dict, text: str) -> tuple[str, list[str]]:
    digits = re.sub(r"\D", "", entity.get("telefon") or "")
    if len(digits) == 10 and digits.startswith("47"):
        digits = digits[2:]
    if len(digits) == 8:
        pattern = r"[\s.()\-]*".join(digits)
        match = re.search(r"(?<!\d)(?:\+?47[\s.()\-]*)?" + pattern + r"(?!\d)", text)
        if match:
            return "registry_phone", [match.group()]
    addr = entity.get("forretningsadresse") or entity.get("postadresse") or {}
    lines = addr.get("adresse") or []
    postcode = addr.get("postnummer") or ""
    if lines and len(lines[0].strip()) >= 5 and postcode:
        street = re.search(r"\s+".join(map(re.escape, lines[0].split())) + r"(?!\w)", text, re.I)
        postal = re.search(rf"(?<!\d){re.escape(postcode)}(?!\d)", text)
        if street and postal:
            field = "business_address" if entity.get("forretningsadresse") else "postal_address"
            return field, [street.group(), postal.group()]
    return "", []


def is_parked(page: Page) -> bool:
    sample = fold(page.title + " " + page.text[:3000])
    if len(page.text) < 120 and not page.jsonld and not find_orgnrs(page.text):
        return True
    return any(marker in sample for marker in (fold(m) for m in PARKED_MARKERS))


def address_owner(page, org, legal_name, entity):
    """Require a single named operator and registry contact in its footer address block."""
    if page.doc is None or find_orgnrs(page.text) - {org}:
        return None
    brand = re.sub(r"\s+(?:as|asa)$", "", fold(legal_name))
    owners = [page.meta.get("og:site_name")] + [
        n.get("legalName") or n.get("name") for n in page.identity_nodes
        if schema_types(n) & {"WebSite", "Organization", "Corporation", "LocalBusiness"}]
    if not brand or fold(owners[0]) not in {brand, fold(legal_name)} or any(
            fold(v) not in {brand, fold(legal_name)} for v in owners if isinstance(v, str)):
        return None
    footers = page.doc.xpath("//footer")
    if len(footers) != 1:
        return None
    footer = footers[0]
    if re.search(r"forretningsforer|forvaltet av|managed by|on behalf of|pa vegne av", fold(footer.text_content())):
        return None
    if any(re.search(r"\b(?:as|asa|borettslag|boligbyggelag)$", fold(t.strip()))
           and fold(t.strip()) != fold(legal_name) for t in footer.itertext()):
        return None
    blocks = [h.getnext() for h in footer.xpath(".//h2|.//h3|.//h4|.//h5|.//h6|.//dt")
              if fold(h.text_content()).strip(" :\n\t") in {"postadresse", "postal address", "mailing address"}]
    if not blocks and urllib.parse.urlsplit(page.url).path in {"", "/"}:
        # A small business may put its brand in the site metadata and its full
        # legal name in the first title segment. Corroborate both on this page.
        if fold(page.title.split("|", 1)[0].strip()) != fold(legal_name):
            return None
        local = [n for n in page.identity_nodes if "LocalBusiness" in schema_types(n)]
        if (len(local) != 1 or not isinstance(local[0].get("name"), str)
                or fold(local[0]["name"]) not in {brand, fold(legal_name)}
                or item_url(local[0].get("url"), page.url) != item_url(page.url, page.url)):
            return None
        address = local[0].get("address")
        registered = entity.get("forretningsadresse") or {}
        postcode = registered.get("postnummer")
        if (not postcode or not isinstance(address, dict) or address.get("addressCountry") != "NO"
                or address.get("postalCode") != postcode or not registered.get("poststed")
                or fold(address.get("addressLocality") if isinstance(address.get("addressLocality"), str) else "")
                != fold(registered["poststed"])):
            return None
        for block in [footer, *footer.xpath(".//address|.//p|.//div")]:
            text = " ".join(" ".join(block.itertext()).split())
            if len(text) > 140:
                continue
            field, spans = contact_proof({"forretningsadresse": registered}, text)
            if spans and re.fullmatch(re.escape(spans[0]) + r"\s*,?\s*(?:NO-)?"
                                      + re.escape(postcode) + r"\s+" + re.escape(registered["poststed"]), text, re.I):
                proof = {k: local[0][k] for k in ("@type", "name", "url") if k in local[0]}
                proof["address"] = {k: address[k] for k in ("addressCountry", "postalCode", "addressLocality")}
                fragment = json.dumps(proof, ensure_ascii=False)
                if len(fragment) <= 600:
                    return page.title, field, [*spans, fragment]
        return None
    if len(blocks) != 1 or blocks[0] is None:
        return None
    lines = [t.strip() for t in blocks[0].itertext() if t.strip()]
    if not lines or fold(lines[0]) != fold(legal_name):
        return None
    text = " ".join(lines)
    field, spans = contact_proof({"telefon": entity.get("telefon"), "postadresse": entity.get("postadresse")}, text)
    if not spans:
        addr = entity.get("postadresse") or {}
        box = re.fullmatch(r"postboks\s+(\d+)", fold((addr.get("adresse") or [""])[0]))
        postcode = addr.get("postnummer")
        if box and postcode:
            match = re.search(r"\bP\.?\s*O\.?\s*Box\s+" + box[1] + r"\b", text, re.I)
            if match and re.search(r"\b" + re.escape(postcode) + r"\b", text):
                field, spans = "postal_address", [match[0], postcode]
    return (lines[0], field, spans) if spans else None


class SiteVisit:
    def __init__(self, candidate: str, source: str):
        self.candidate = candidate
        self.source = source
        self.pages: list[Page] = []
        self.decision = "unchecked"
        self.reason = ""
        self.proof_page: Page | None = None
        self.proof_span = ""
        self.contact_field = ""
        self.contact_spans: list[str] = []
        self.address_entity = None
        self.foreign_orgs: set[str] = set()
        self.budget_incomplete = False

    @property
    def decision_code(self) -> str:
        if self.decision == "accepted":
            return "exact_org" if "organisation number printed" in self.reason else "full_legal_name"
        if self.foreign_orgs:
            return "ownership_conflict"
        return {"ambiguous": "identity_unproven", "rejected": "identity_rejected",
                "related_site": "related_entity", "blocked": "robots_blocked",
                "budget": "budget_unattempted", "unreachable": "fetch_failed"}.get(self.decision, self.decision)

    @property
    def origin(self) -> str:
        page = self.pages[0] if self.pages else None
        url = page.url if page else self.candidate
        parts = urllib.parse.urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}/"


def _span_around(text: str, needle_re: str, width: int = 90) -> str:
    m = re.search(needle_re, text)
    if not m:
        return ""
    return text[max(0, m.start() - width): m.end() + width].strip()


def org_pattern(org: str) -> str:
    return rf"{org[:3]}[\s .\-]?{org[3:6]}[\s .\-]?{org[6:]}"


def address_tokens(entity: dict) -> set[str]:
    out: set[str] = set()
    for key in ("forretningsadresse", "postadresse"):
        addr = entity.get(key) or {}
        for line in (addr.get("adresse") or []) + [addr.get("poststed") or "", addr.get("kommune") or ""]:
            out |= set(re.findall(r"[a-z0-9]+", fold(line)))
    return out


def identity_tokens(entity: dict, legal_name: str) -> list[str]:
    """Distinctive legal-name tokens that are *not* simply the company's own address (e.g. 'Hinderveien 2 AS')."""
    addr = address_tokens(entity)
    return [t for t in distinctive_tokens(legal_name) if t not in addr]


def _footer_text(page: Page) -> str:
    if page.doc is None:
        return page.text[-1500:]
    feet = page.doc.xpath("//footer")
    return " ".join(f.text_content() for f in feet)[:4000] if feet else page.text[-1500:]


def visit_site(fetcher: Fetcher, candidate: str, source: str, org: str, entity: dict, legal_name: str,
               related_orgs: set[str], max_subpages: int = 3, person_tokens: set[str] | None = None) -> SiteVisit:
    visit = SiteVisit(candidate, source)
    host = urllib.parse.urlsplit(candidate).hostname or ""
    if not host_is_public(host):
        alt = host[4:] if host.startswith("www.") else "www." + host
        if host_is_public(alt):
            candidate = candidate.replace(host, alt, 1)
            visit.candidate = candidate
    snap = fetcher.get(candidate, phase="web")
    if snap.status == 0 and snap.error in {"ConnectError", "ConnectTimeout", "ReadTimeout"} and candidate.startswith("https://"):
        snap = fetcher.get("http://" + candidate[len("https://"):], phase="web")
    if snap.error == "blocked_robots":
        visit.decision, visit.reason = "blocked", "robots.txt disallows the homepage or its policy could not be read"
        return visit
    if not snap.ok or "html" not in (snap.content_type or "html"):
        visit.decision, visit.reason = "unreachable", f"homepage not reachable ({snap.status or snap.error})"
        return visit
    home = Page(snap)
    visit.pages.append(home)
    final_host = urllib.parse.urlsplit(home.url).hostname or ""
    if any(final_host == h or final_host.endswith("." + h) for h in NON_COMPANY_HOSTS):
        visit.decision, visit.reason = "rejected", f"redirects to a non-company platform ({final_host})"
        return visit
    redirected = registrable_domain(home.url) != registrable_domain(candidate)
    if redirected:
        # cross-domain redirect: only an exact organisation number on the destination can prove identity
        visit.reason = f"redirected to {registrable_domain(home.url)}; "
    if is_parked(home):
        visit.decision, visit.reason = "rejected", "parked / placeholder / empty site"
        return visit
    multi_entity = False

    def scan(page: Page) -> bool:
        nonlocal multi_entity
        orgs = find_orgnrs(page.text + " " + " ".join(json.dumps({k: v for k, v in n.items() if k in
                            {"name", "legalName", "identifier", "taxID", "vatID"}}, ensure_ascii=False) for n in page.identity_nodes))
        others = {o for o in orgs if o != org}
        if org in orgs:
            if others or visit.foreign_orgs:
                # several organisation numbers on one page (group/portfolio/client list): not proof of ownership
                multi_entity = True
                visit.foreign_orgs |= others
                return False
            footer_orgs = find_orgnrs(_footer_text(page)) if page.doc is not None and page.doc.xpath("//footer") else set()
            owner_context = _span_around(page.text, org_pattern(org), width=220)
            if re.search(r"(?:website by|webdesign by|developed by|laget av|designet av).{0,120}" + org_pattern(org), fold(owner_context)):
                multi_entity = True
                return False
            named_invoicing_entity = (exact_name_present(legal_name, owner_context)
                                     and re.search(r"send.{0,40}faktura|faktura.{0,25}(ehf|adresse)|selger|ansvarlig for", fold(owner_context)))
            if footer_orgs != {org} and not page.identity_quote(legal_name) and not named_invoicing_entity:
                multi_entity = True
                return False
            visit.proof_page = page
            visit.proof_span = _span_around(page.text, org_pattern(org)) or next(
                (_span_around(raw, org_pattern(org)) for raw in page.jsonld_raw.values() if re.search(org_pattern(org), raw)), "")
            return True
        visit.foreign_orgs |= others
        return False

    proved_home = scan(home)
    if (not proved_home and source == "registry_declared" and not redirected and not multi_entity
            and not visit.foreign_orgs and not (set(name_tokens(legal_name)) & HOLDING_WORDS)
            and (owner := address_owner(home, org, legal_name, entity))):
        visit.proof_page, visit.address_entity = home, entity
        visit.proof_span, visit.contact_field, visit.contact_spans = owner
        visit.decision, visit.reason = "accepted", "exact legal name with matching registry contact and company operator evidence"
        return visit
    if not proved_home:
        # follow likely legal/contact pages on the same site
        seen = {home.url.rstrip("/")}
        targets = []
        for url, text in home.links:
            if urllib.parse.urlsplit(url).hostname != urllib.parse.urlsplit(home.url).hostname:
                continue
            if url.rstrip("/") in seen or re.search(r"\.(pdf|jpg|png|zip|docx?)$", url, re.I):
                continue
            if SUBPAGE_HINTS.search(urllib.parse.urlsplit(url).path) or SUBPAGE_HINTS.search(fold(text)):
                seen.add(url.rstrip("/"))
                targets.append(url)
        if len(targets) < 2:
            base = f"{urllib.parse.urlsplit(home.url).scheme}://{urllib.parse.urlsplit(home.url).netloc}"
            for path in ("/kontakt", "/kontakt-oss", "/om-oss"):
                if base + path not in seen and len(targets) < 3:
                    targets.append(base + path)
        targets.sort(key=lambda u: (0 if re.search(r"kontakt|contact", u, re.I) else 1 if re.search(r"om-oss|about", u, re.I) else 2))
        for url in targets[:max_subpages]:
            try:
                sub = fetcher.get(url, phase="web")
            except BudgetExhausted:
                visit.budget_incomplete = True
                break
            if not sub.ok or urllib.parse.urlsplit(sub.final_url).hostname != urllib.parse.urlsplit(home.url).hostname:
                continue
            page = Page(sub)
            visit.pages.append(page)
            if scan(page):
                break

    if visit.proof_page is not None:
        visit.decision = "accepted"
        visit.reason += "exact organisation number printed on the site"
        return visit
    if visit.budget_incomplete:
        visit.decision, visit.reason = "budget", "identity traversal interrupted by request/time budget"
        return visit
    # conflicting org number: this is somebody else's site (parent, brand, sister, accountant, web agency…)
    owner_conflict = visit.foreign_orgs - related_orgs
    if visit.foreign_orgs:
        rel = visit.foreign_orgs & related_orgs
        if rel:
            visit.decision = "related_site"
            visit.reason += f"site belongs to related entity {sorted(rel)[0]} (group relation) — labelled, not merged"
        else:
            visit.decision = "rejected"
            visit.reason += f"site presents a different organisation number ({sorted(owner_conflict)[0]})"
        return visit

    if multi_entity:
        visit.decision = "ambiguous"
        visit.reason += "organisation number appears only among several companies' numbers (group/portfolio page)"
        return visit
    if redirected:
        visit.decision = "ambiguous"
        visit.reason += "cross-domain redirect without the exact organisation number on the destination"
        return visit
    tokens = identity_tokens(entity, legal_name)
    if set(name_tokens(legal_name)) & HOLDING_WORDS:
        visit.decision, visit.reason = "ambiguous", visit.reason + "holding/investment company: only the exact organisation number can prove the site is its own"
        return visit
    if tokens and person_tokens and set(tokens) <= person_tokens:
        visit.decision, visit.reason = "ambiguous", visit.reason + "legal name consists of a role holder's personal name; needs the organisation number"
        return visit
    if not tokens:
        visit.decision, visit.reason = "ambiguous", visit.reason + "legal name is too generic (or is just the address) to verify without an organisation number"
        return visit
    name_in_identity = bool(home.identity_quote(legal_name))
    emails = [e for e in [(entity.get("epostadresse") or "").lower(), *entity.get("_unit_emails", [])] if "@" in e]
    match = [e for e in emails if registrable_domain(e.split("@", 1)[1]) == registrable_domain(home.url)]
    email = match[0] if match else ""
    email_domain_match = bool(match) and email.split("@", 1)[1] not in FREE_MAIL
    if source == "registry_email_domain" and email_domain_match and home.doc is not None:
        # The footer must identify its own homepage, in the operator's registered
        # contact context. A customer link elsewhere on the site cannot qualify.
        footers = home.doc.xpath("//div[contains(concat(' ',normalize-space(@class),' '),' footer-info ')]") or home.doc.xpath("//footer")
        owner_name = (home.meta.get("og:site_name") or "").split("|", 1)[0].strip()
        if len(footers) == 1 and fold(owner_name) == fold(legal_name):
            footer = footers[0]
            self_links = [a for a in footer.xpath(".//a[@href]") if
                          item_url(a.get("href"), home.url) == item_url(home.url, home.url)
                          and fold(a.text_content().strip()) == fold(legal_name)]
            field, spans = contact_proof({"forretningsadresse": entity.get("forretningsadresse")},
                                         " ".join(footer.itertext()))
            operators = [n.get("legalName") or n.get("name") for n in home.identity_nodes
                         if schema_types(n) & {"Organization", "Corporation", "LocalBusiness", "WebSite"}]
            allowed = {fold(legal_name), fold(home.meta["og:site_name"])}
            conflicts = any(isinstance(v, str) and fold(v) not in allowed for v in operators)
            if self_links and spans and not conflicts and not re.search(
                    r"managed by|forretningsforer|pa vegne av|on behalf of|website by|laget av",
                    fold(footer.text_content())):
                contact_spans = [*spans, home.meta["og:site_name"],
                    etree.tostring(self_links[0], method="html", encoding="unicode", with_tail=False)]
                if all(len(span) <= 600 for span in contact_spans):
                    visit.proof_page, visit.proof_span = home, self_links[0].text_content().strip()
                    visit.contact_field, visit.contact_spans = field, contact_spans
                    visit.decision, visit.reason = "accepted", "registered email domain, exact operator self-link and registry business address"
                    return visit
    if name_in_identity and email_domain_match:
        visit.decision = "accepted"
        visit.proof_page = visit.pages[0]
        visit.proof_span = home.identity_quote(legal_name)
        visit.reason += "the company's registered e-mail domain is this site's domain and the legal name is in its identity fields"
        return visit
    contact_pages = [home]
    if source == "registry_declared":
        linked = {item_url(url, home.url) for url, _ in home.links}
        contact_pages.extend(p for p in visit.pages[1:] if item_url(p.url, home.url) in linked
                             and urllib.parse.urlsplit(p.url).netloc == urllib.parse.urlsplit(home.url).netloc)
    for contact_page in contact_pages:
        if not registrable_domain(home.url).endswith(".no") or not contact_page.identity_quote(legal_name):
            continue
        field, spans = contact_proof(entity, contact_page.text)
        if not spans:
            continue
        visit.decision = "accepted"
        visit.contact_field, visit.contact_spans = field, spans
        visit.proof_page = contact_page
        visit.proof_span = contact_page.identity_quote(legal_name)
        visit.reason += "legal name in the site's identity fields and registry phone/address on the site"
        return visit
    if source in DECLARED_BY and home.identity_quote(legal_name, allow_title=False):
        visit.decision = "accepted"
        visit.proof_page = home
        visit.proof_span = home.identity_quote(legal_name)
        visit.reason += DECLARED_BY[source] + " and the site's identity fields carry the legal name"
        return visit
    visit.decision = "ambiguous"
    visit.reason += "no organisation number and insufficient name/contact evidence"
    return visit


def domain_candidates(entity: dict, bulk_row: dict | None, extra: list[tuple[str, str]] | None = None, *,
                      include_guesses: bool = True) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def push(url: str | None, source: str) -> None:
        site = normalize_site(url)
        if not site:
            return
        dom = site.rstrip("/")
        if dom in seen:
            return
        seen.add(dom)
        out.append((site, source))

    for row in (entity, bulk_row or {}):
        push(row.get("hjemmeside"), "registry_declared")
    email = (bulk_row or {}).get("epostadresse") or entity.get("epostadresse")
    if email and "@" in email:
        dom = email.split("@", 1)[1].strip().lower()
        if dom not in FREE_MAIL and not any(dom.endswith(f) for f in ("online.no",)):
            push(dom, "registry_email_domain")
    for url, source in extra or []:
        if source == "wikidata_p856":
            push(url, source)
    for url, source in extra or []:
        if source == "subunit_email_domain" and url.lower() in FREE_MAIL:
            continue
        if source != "wikidata_p856":
            push(url, source)
    if not include_guesses:
        return out
    tokens = [t for t in name_tokens(entity.get("navn")) if t not in ("og", "and", "i", "pa")]
    distinct = distinctive_tokens(entity.get("navn"))
    if distinct and 1 <= len(tokens) <= 4 and not set(tokens) & HOLDING_WORDS:
        joined = "".join(tokens)
        core = "".join(t for t in tokens if t not in GENERIC_TOKENS)
        variants = [joined + ".no", "-".join(tokens) + ".no" if len(tokens) > 1 else None, joined + "as.no",
                    core + ".no" if core != joined and len(core) >= 6 else None]
        guesses = 0
        for cand in variants:
            if cand and len(cand.split(".")[0]) >= 5 and guesses < 2 and host_is_public(cand):
                before = len(out)
                push(cand, "name_slug_guess")
                guesses += len(out) - before
    return out


# ------------------------------------------------------------------------------------------ extraction

def _social_ok(platform: str, url: str, page: Page, legal_name: str, domain: str, sameas: set[str], org: str = "") -> bool:
    handle = fold(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).strip("/@ ")
    handle = re.sub(r"^(company|school|showcase|channel|c|user|pages?)/", "", handle)
    compact = re.sub(r"[^a-z0-9]", "", handle)
    expected = "".join(name_tokens(legal_name))
    full = re.sub(r"[^a-z0-9]", "", fold(legal_name))
    # Neither a shared domain nor sameAs identifies which legal entity owns an account.
    if len(expected) < 3 or compact not in {expected, full}:
        return False
    # A short single brand (Otis, etc.) is shared by regional entities. Require
    # the legal-form handle, or an explicit account declaration by this entity.
    if len(name_tokens(legal_name)) == 1 and compact != full:
        return any(schema_types(n) & {"Organization", "Corporation", "LocalBusiness"} and _employer_matches(n, org, legal_name) and url.rstrip("/") in
                   {s.rstrip("/") for s in (n.get("sameAs") if isinstance(n.get("sameAs"), list) else [n.get("sameAs")]) if isinstance(s, str)}
                   for n in page.identity_nodes)
    return True


def extract_company_owned(pb: ProfileBuilder, fetcher: Fetcher, visit: SiteVisit, legal_name: str, *, want_news: bool = True, defer_enrichment: bool = False) -> None:
    if visit.decision != "accepted" or not visit.pages:
        return
    pb.extra["legal_name"] = legal_name
    home = visit.pages[0]
    domain = registrable_domain(home.url)
    origin = visit.origin
    proof = visit.proof_page or home
    # When only a subsidiary contact/legal page identifies this entity, publish
    # that verified page rather than the surrounding corporate homepage.
    owned = home if page_attributed(home, pb.org, legal_name) else proof
    scope_path = urllib.parse.urlsplit(owned.url).path.rstrip("/") or "/"
    pb.extra["website_identity"] = {
        "organisation_number": pb.org, "legal_name": legal_name, "decision": "accepted",
        "method": visit.decision_code, "proof_url": proof.url, "proof_span": visit.proof_span or home.title,
        "scope_host": urllib.parse.urlsplit(owned.url).hostname, "scope_path": scope_path,
        "relationship": "exact_legal_entity",
    }
    ev_site = pb.add_evidence(Evidence(proof.url, "company_owned", proof.snap.retrieved_at, proof.snap.sha256, visit.proof_span or home.title,
                                       f"identity_gate:{visit.source}", identity_reason=visit.reason))
    support = [ev_site]
    for span in visit.contact_spans:
        support.append(pb.add_evidence(Evidence(proof.url, "company_owned", proof.snap.retrieved_at,
                                               proof.snap.sha256, span, f"identity_contact:{visit.contact_field}")))
    for c in pb.claims.values():
        if c.field == visit.contact_field:
            support.extend(c.evidence_ids)
    pb.add(Claim("website", "official_website", owned.url, support, label="Official website" if owned is home else "Verified company page",
                 confidence=1.0 if "organisation number" in visit.reason else 0.9, note=f"discovered via {visit.source}"))
    pb.set_state("website", "available", visit.reason, visit.candidate)

    # public brand (site name differs from legal name)
    brand = home.meta.get("og:site_name") or next((n.get("name") for n in home.identity_nodes if isinstance(n.get("name"), str) and "Organization" in str(n.get("@type", ""))), None)
    if owned is home and brand and 2 < len(brand) < 60 and fold(brand) not in fold(legal_name) and fold(legal_name).split(" ")[0] not in fold(brand).split(" ")[:1]:
        ev = pb.add_evidence(Evidence(home.url, "company_owned", home.snap.retrieved_at, home.snap.sha256, brand, "html_meta:og:site_name"))
        pb.add(Claim("identity", "public_brand", brand, [ev, ev_site], label="Public brand (from verified site)", confidence=0.9))

    # social profiles: outbound links on the verified site (company-owned declarations)
    socials: dict[str, tuple[str, Page, str]] = {}
    for page in visit.pages:
        if not in_verified_scope(page, visit, pb.org, legal_name):
            continue
        sameas = {s.rstrip("/") for node in page.jsonld for s in
                  (node.get("sameAs") if isinstance(node.get("sameAs"), list) else [node.get("sameAs")]) if isinstance(s, str)}
        for url, _text in page.links + [(s, "") for s in sameas]:
            for platform, pattern in SOCIAL_PATTERNS.items():
                m = pattern.match(url)
                if m and platform not in socials:
                    clean = m.group(0).rstrip("/")
                    if _social_ok(platform, clean, page, legal_name, domain, sameas, pb.org):
                        socials[platform] = (clean, page, url)
    for platform, (url, page, original) in socials.items():
        ev = pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at, page.snap.sha256, original, "html_link:outbound_social",
                                      identity_reason="linked from the verified official website; handle matches the company name/domain"))
        pb.add(Claim("social_profiles", platform, url, [ev, ev_site], label=platform.replace("_", "/").title() + " profile", key=f"social:{platform}"))
    pb.set_state("social_profiles", "available" if socials else "not_available",
                 f"{len(socials)} company-owned profiles linked from the verified site" if socials else "verified site links no company-owned social profiles", origin)

    # contact e-mail: role mailboxes on the company's own domain only (no personal addresses)
    mails: dict[str, Page] = {}
    for page in visit.pages:
        if not in_verified_scope(page, visit, pb.org, legal_name):
            continue
        found = set(EMAIL_RE.findall(page.text)) | {u[7:].split("?")[0] for u, _ in page.links if u.lower().startswith("mailto:")}
        for mail in found:
            mail = mail.strip().lower().rstrip(".")
            local, _, dom = mail.partition("@")
            if registrable_domain(dom) == domain and local in ROLE_MAILBOXES:
                mails.setdefault(mail, page)
    for mail, page in list(mails.items())[:3]:
        ev = pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at, page.snap.sha256, mail, "html_text:email_regex+role_mailbox_filter"))
        pb.add(Claim("contact", "email", mail, [ev, ev_site], label="Contact e-mail (company domain)", key=f"email:{mail}"))
    if mails:
        pb.set_state("contact", "available", "company role mailbox on verified site", origin)
    else:
        pb.set_state("contact", "not_available", "no company role mailbox on the verified site", origin)

    # self-description (company-owned promotional copy, labelled as such)
    desc = home.meta.get("description") or home.meta.get("og:description")
    if not desc:
        desc = next((n.get("description") for n in home.jsonld if isinstance(n.get("description"), str)), None)
    if desc and page_attributed(home, pb.org, legal_name) and 40 <= len(desc) <= 600 and not any(fold(m) in fold(desc) for m in PARKED_MARKERS):
        ev = pb.add_evidence(Evidence(home.url, "company_owned", home.snap.retrieved_at, home.snap.sha256, desc[:600], "html_meta:description"))
        pb.add(Claim("description", "self_description", desc, [ev, ev_site], label="Company's own description (promotional, company-owned)", confidence=0.9))
        pb.set_state("description", "available", "meta description on verified site", origin)
    else:
        pb.set_state("description", "not_available", "verified site has no usable description", origin)

    if defer_enrichment:
        pb.extra["deferred_site"] = visit
        return
    enrich_company_owned(pb, fetcher, visit, want_news=want_news)


def enrich_company_owned(pb: ProfileBuilder, fetcher: Fetcher, visit: SiteVisit, *, want_news: bool = True) -> None:
    """Optional detail discovery after the initial company verification pass."""
    if visit.decision != "accepted" or not visit.pages:
        return
    home = visit.pages[0]
    domain = registrable_domain(home.url)
    origin = visit.origin
    # Discover individual ads from the company careers page within a small, bounded crawl.
    eligible = [p for p in visit.pages if in_verified_scope(p, visit, pb.org, pb.extra.get("legal_name", ""))]
    job_hint = re.compile(r"\b(?:careers?|karriere\w*|ledig\w*|vacanc\w*|jobb\w*|jobs?|stillingen|stillinger|stilling|available-positions)\b")
    def careers_links(page):
        return [(url, page.url) for raw, txt in page.links if (url := item_url(raw, page.url))
                and urllib.parse.urlsplit(url).hostname == urllib.parse.urlsplit(home.url).hostname
                and job_hint.search(fold(urllib.parse.urlsplit(url).path + " " + txt))]
    job_links = [link for p in eligible for link in careers_links(p)]
    job_links = [(u, p.url) for p in eligible for node in p.jsonld if "JobPosting" in schema_types(node)
                 for u in [item_url(node.get("url"), p.url)] if u and registrable_domain(u) == domain] + job_links
    if not job_links:
        pb.trace_discovery("careers", home.url, home.url, "no_careers_link")
    fetched_jobs = set()
    try:
        while job_links and len(fetched_jobs) < 2:
            url, linked_from = job_links.pop(0)
            if url in fetched_jobs or url in {p.url for p in visit.pages}:
                continue
            fetched_jobs.add(url)
            job_snap = fetcher.get(url, phase="web_news")
            pb.trace_discovery("careers", linked_from, url, "fetched" if job_snap.ok else "fetch_failed")
            if job_snap.ok and registrable_domain(job_snap.final_url) == domain:
                job_page = Page(job_snap)
                if not in_verified_scope(job_page, visit, pb.org, pb.extra.get("legal_name", "")):
                    pb.trace_discovery("careers", linked_from, job_page.url, "identity_unproven")
                    continue
                visit.pages.append(job_page)
                details = [link for link in careers_links(job_page) if single_item_url(link[0], "jobs")]
                structured = [(u, job_page.url) for node in job_page.jsonld if "JobPosting" in schema_types(node)
                              for u in [item_url(node.get("url"), job_page.url)] if u and registrable_domain(u) == domain]
                job_links[:0] = structured + details
                if not any("JobPosting" in schema_types(n) for n in job_page.jsonld):
                    html_vacancy(pb, visit, job_page, linked_from)
    except BudgetExhausted:
        pb.trace_discovery("careers", linked_from, url, "budget_exhausted")
    _site_jobs(pb, visit)
    from .ats import greenhouse_jobs
    greenhouse_jobs(pb, fetcher, visit.pages, pb.extra.get("legal_name", ""))
    if want_news:
        _news(pb, fetcher, visit, origin)


def _employer_matches(node: object, org: str, legal_name: str) -> bool:
    if not isinstance(node, dict):
        return False
    identifiers = [node.get(k) for k in ("identifier", "taxID", "vatID")]
    numbers = set()
    for value in identifiers:
        values = value if isinstance(value, list) else [value]
        for v in values:
            if isinstance(v, dict):
                v = v.get("value")
            if isinstance(v, (str, int)):
                numbers.update("".join(m.groups()) for m in ORG_RE.finditer(str(v)))
    if numbers:
        return numbers == {org}
    name = node.get("legalName") or node.get("name")
    return (isinstance(name, str) and bool(name_tokens(legal_name))
            and re.findall(r"[a-z0-9]+", fold(name)) == re.findall(r"[a-z0-9]+", fold(legal_name)))


def _resolved_publisher(page: Page, publisher: object) -> object:
    """Resolve a unique same-document Organization reference without fetching it."""
    if not isinstance(publisher, dict) or set(publisher) != {"@id"} or not isinstance(publisher.get("@id"), str):
        return publisher
    ref = urllib.parse.urljoin(page.url, publisher["@id"])
    matches = [n for n in page.jsonld if isinstance(n.get("@id"), str)
               and urllib.parse.urljoin(page.url, n["@id"]) == ref
               and schema_types(n) & {"Organization", "Corporation", "LocalBusiness"}]
    if len(matches) != 1:
        return publisher
    return matches[0]


def _organization_excerpt(node: dict) -> dict:
    """Keep the identity fields checked by the gate without contact details."""
    def identifier(value):
        if isinstance(value, (str, int)):
            return value
        if isinstance(value, dict) and isinstance(value.get("value"), (str, int)):
            return {"value": value["value"]}
        return None

    excerpt = {key: node[key] for key in ("legalName", "name") if isinstance(node.get(key), str)}
    for key in ("identifier", "taxID", "vatID"):
        value = node.get(key)
        if isinstance(value, list):
            identifiers = [identifier(item) for item in value]
            if all(item is not None for item in identifiers):
                excerpt[key] = identifiers
        elif (selected := identifier(value)) is not None:
            excerpt[key] = selected
    return excerpt


def vacancy_day(text):
    value = fold(text).strip()
    months = "januar februar mars april mai juni juli august september oktober november desember".split()
    match = re.fullmatch(r"(\d{1,2})\.?\s+(\w+)\s+(\d{4})", value)
    if match and match[2] in months:
        value = f"{match[3]}-{months.index(match[2]) + 1:02}-{int(match[1]):02}"
    elif re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
        value = "-".join(reversed(value.split(".")))
    return parse_job_date(value)


def html_vacancy(pb, visit, page, origin):
    """Read a single first-party ad reached through the careers traversal."""
    def outcome(reason):
        pb.trace_discovery("site_job", origin, page.url, reason)

    name = pb.extra.get("legal_name", "")
    if page.doc is None or not in_verified_scope(page, visit, pb.org, name):
        return outcome("identity_unproven")
    roots = page.doc.xpath("//main//article|//article[not(ancestor::main)]")
    if not roots:
        roots = page.doc.xpath("//main")
    if len(roots) != 1:
        return outcome("single_ad_unproven")
    root = roots[0]
    heads = root.xpath(".//h1")
    if len(heads) != 1:
        return outcome("single_ad_unproven")
    title = " ".join(heads[0].text_content().split())
    if fold(title) in {"ledig stilling", "ledige stillinger", "careers", "vacancies", "jobs"}:
        roles = heads[0].xpath("following::*[self::h2 or self::h3 or self::h4 or self::h5][1]")
        title = " ".join(roles[0].text_content().split()) if roles and root in roles[0].iterancestors() else ""
    elements = root.xpath(".//*[self::p or self::li or self::dt or self::dd or self::div or self::span or self::strong or self::h4 or self::a or self::time][not(ancestor::nav or ancestor::aside or ancestor::footer)]")
    lines = []
    for el in elements:
        if el.tag == "div" and len(el):
            continue
        value = " ".join(el.text_content().split())
        if value and len(value) <= 600:
            lines.append(value)
    brand = re.sub(r"\s+(?:as|asa)$", "", fold(name))
    names = {fold(name)}
    if visit.address_entity and address_owner(page, pb.org, name, visit.address_entity):
        names.add(brand)
    labels = [fold(s).split(":", 1)[1].strip() for s in lines if re.match(r"^(arbeidsgiver|employer)\s*:", fold(s))]
    employer = next((s for s in lines for n in names if re.fullmatch(
        r"(?:arbeidsgiver|employer)\s*:\s*" + re.escape(n), fold(s)) or re.search(
        r"(?:^" + re.escape(n) + r" soker\b|\bstillinger i " + re.escape(n) + r"[.!]?\s*$)", fold(s))), None)
    employer_verified = employer and all(label in names for label in labels) and not any(
        re.search(r"\b(?:pa vegne av|on behalf of|for var kunde|for our client)\b", fold(s)) for s in lines)
    closure = next((line for line in lines if re.fullmatch(
        r"(?:applications (?:are )?closed|this vacancy is no longer available|stillingen er (?:besatt|utlopt)|soknadsfristen er utlopt)[.!]?",
        fold(line))), None)
    if closure and title and single_item_url(page.url, "jobs"):
        if not employer_verified:
            return outcome("employer_unproven")
        ids = [pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at,
                                       page.snap.sha256, span, "html:vacancy_closure"))
               for span in (title, employer, closure)]
        pb.extra.setdefault("closed_jobs", {})[f"sitejob:{page.url}"] = {"title": title, "evidence_ids": ids}
        return outcome("closed")
    dates = {}
    for el in elements:
        line = " ".join(el.text_content().split())
        if len(line) > 600:
            continue
        match = re.fullmatch(r"(søknadsfrist|application deadline|publisert|published|date posted)\s*:?\s*(.*)", line, re.I)
        if match:
            sibling = el.getnext()
            raw = match[2] or (el.tail or "").strip() or (
                sibling.text_content().strip() if sibling is not None and hasattr(sibling, "text_content") else "")
            leading = re.match(r"(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\.?\s+[A-Za-zæøåÆØÅ]+\s+\d{4})(?=$|[.\s])", raw)
            if not leading:
                continue
            raw = leading[1]
            key = "deadline" if fold(match[1]) in {"soknadsfrist", "application deadline"} else "posted"
            dates.setdefault(key, {}).setdefault(vacancy_day(raw), (line, raw))
    now = datetime.now(timezone.utc)
    deadlines = dates.get("deadline", {})
    if len(deadlines) != 1 or not (deadline := next(iter(deadlines))):
        return outcome("open_status_unproven")
    if job_expired(deadline, now):
        return outcome("expired")
    if not title or not single_item_url(page.url, "jobs") or any(re.search(
            r"applications? (?:are )?closed|no longer accepting|stillingen er (besatt|utlopt)|soknadsfristen er utlopt", fold(s)) for s in lines):
        return outcome("single_open_ad_unproven")
    applications = [el for el in elements if el.tag == "a" and fold(el.text_content().strip()) in
                    {"sok her", "sok na", "sok pa stillingen", "apply", "apply now", "apply for this job"}
                    and (item_url(el.get("href"), page.url) or (el.get("href") or "").startswith("mailto:"))]
    destinations = {item_url(a.get("href"), page.url) or a.get("href") for a in applications}
    if len(destinations) != 1 or any((a.get("href") or "").strip().startswith("#") for a in applications):
        return outcome("application_route_unproven")
    if not employer_verified:
        return outcome("employer_unproven")
    proofs = [title, employer, etree.tostring(applications[0], method="html", encoding="unicode", with_tail=False)]
    proofs.extend(deadlines[deadline])
    posted_rows = dates.get("posted", {})
    if len(posted_rows) == 1:
        posted = next(iter(posted_rows))
        proofs.extend(posted_rows[posted])
    elif not posted_rows:
        nodes = [n for n in page.identity_nodes if "WebPage" in schema_types(n)
                 and item_url(n.get("url") or n.get("@id"), page.url) == item_url(page.url, page.url)
                 and isinstance(n.get("name"), str) and fold(n["name"]).split(" - ")[0] == fold(title)]
        posted = parse_job_date(nodes[0].get("datePublished")) if len(nodes) == 1 else None
        if posted:
            proofs.append(json.dumps({"datePublished": nodes[0]["datePublished"]}, ensure_ascii=False))
    else:
        posted = None
    if not posted or job_not_yet_published(posted, now) or any(len(s) > 600 for s in proofs):
        return outcome("publication_unproven")
    ids = [pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at, page.snap.sha256,
                           s, "html:individual_vacancy", identity_reason="employer in verified vacancy"))
           for s in dict.fromkeys(proofs)]
    ids.extend(eid for c in pb.family_claims("website") for eid in c.evidence_ids)
    value = dict(title=title, employer=name, url=page.url, published=posted.isoformat(),
                 expires=deadline.isoformat(), source="company website")
    pb.add(Claim("jobs", "job_posting", value, ids, label="Job posting (company website)",
                 key=f"sitejob:{page.url}", effective_date=posted.isoformat()))
    pb.set_state("jobs", "available", "open individual ad on verified company site", page.url)
    outcome("published")


def _site_jobs(pb: ProfileBuilder, visit: SiteVisit) -> None:
    """Publish distinct, dated ads with exact hiring-organization evidence."""
    now = datetime.now(timezone.utc)
    legal_name = pb.extra.get("legal_name") or next((c.value for c in pb.family_claims("identity") if c.field == "legal_name"), "")
    for page in visit.pages:
        # Ignore closure notices in navigation/recommendations for other vacancies.
        closure_text = page.text
        if page.doc is not None:
            roots = page.doc.xpath("//main|//article")
            root = roots[0] if roots else page.doc
            closure_text = " ".join(root.xpath(".//text()[not(ancestor::aside or ancestor::nav or ancestor::footer or ancestor::script)]"))
        closed = re.search(r"\b(?:applications? (?:are )?closed|no longer accepting applications|"
                           r"(?:this )?(?:vacancy|job posting) is no longer available|"
                           r"soknadsfristen (?:er )?utlopt|stillingen er (?:besatt|utlopt)|"
                           r"(?:denne )?stillingen er ikke lenger tilgjengelig)\b", fold(closure_text))
        if closed and page.doc is not None:
            spans = [" ".join(el.text_content().split()) for el in root.xpath(
                ".//*[not(ancestor-or-self::aside or ancestor-or-self::nav or ancestor-or-self::footer or ancestor-or-self::script)]")]
            matches = [span for span in spans if closed.re.search(fold(span))]
            if matches:
                closure_text = min(matches, key=len)
        for node in page.jsonld:
            if "JobPosting" not in schema_types(node):
                continue
            title = node.get("title") or node.get("name")
            valid = parse_job_date(node.get("validThrough"))
            posted = parse_job_date(node.get("datePosted"))
            url = item_url(node.get("url") or page.url, page.url)
            if (closed and url and single_item_url(url, "jobs") and url == item_url(page.url, page.url)
                    and _employer_matches(node.get("hiringOrganization"), pb.org, legal_name)):
                if not isinstance(title, str) or not title.strip():
                    continue
                title_field = "title" if node.get("title") else "name"
                proof = json.dumps({title_field: title, "hiringOrganization": _organization_excerpt(node["hiringOrganization"])}, ensure_ascii=False)
                if len(proof) <= 600 and len(closure_text.strip()) <= 600:
                    ids = [pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at,
                           page.snap.sha256, span, method)) for span, method in
                           ((proof, "jsonld:JobPosting"), (closure_text.strip(), "job:explicit_closure"))]
                    pb.extra.setdefault("closed_jobs", {})[f"sitejob:{url}"] = {
                        "title": title.strip()[:160], "evidence_ids": ids}
                continue
            reason = None
            if closed:
                reason = "closed"
            elif not isinstance(title, str) or not title.strip():
                reason = "missing_title"
            elif not posted or job_not_yet_published(posted, now):
                reason = "invalid_publication_date"
            elif (node.get("validThrough") not in (None, "") and not valid) or (valid and job_expired(valid, now)):
                reason = "expired_or_invalid_deadline"
            elif not url or not single_item_url(url, "jobs") or url != item_url(page.url, page.url):
                reason = "not_detail"
            elif not _employer_matches(node.get("hiringOrganization"), pb.org, legal_name):
                reason = "wrong_employer"
            elif not valid and (node.get("directApply") is not True or job_expired(posted, now - timedelta(days=90))):
                reason = "open_status_unproven"
            if reason:
                pb.trace_discovery("site_job", page.url, url or page.url, reason)
                continue
            title_field = "title" if node.get("title") else "name"
            proof = {key: node[key] for key in (title_field, "datePosted", "validThrough", "directApply") if key in node}
            employer = _organization_excerpt(node["hiringOrganization"])
            if not _employer_matches(employer, pb.org, legal_name):
                continue
            proof["hiringOrganization"] = employer
            excerpt = json.dumps(proof, ensure_ascii=False)
            if len(excerpt) > 600:
                continue
            published = posted.isoformat()
            expires = valid.isoformat() if valid else None
            value = {k: v for k, v in {"title": title.strip()[:160], "published": published, "expires": expires, "url": url,
                     "employer": legal_name, "source": "company website (schema.org JobPosting)"}.items() if v}
            ev = pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at, page.snap.sha256,
                                          excerpt, "jsonld:JobPosting", identity_reason="hiringOrganization matches the exact company",
                                          reporting_period={"from": published, "to": expires or ""}))
            pb.add(Claim("jobs", "job_posting", value, [ev], label="Job posting (company website)",
                         key=f"sitejob:{url}", effective_date=published))
            pb.set_state("jobs", "available", "dated job posting with exact hiring organization", page.url)
            pb.trace_discovery("site_job", page.url, url, "published")
    # A bounded site crawl cannot establish that a missing old ad has closed.
    pb.extra.setdefault("incomplete_families", {})["jobs"] = "bounded website/NAV discovery is not an exhaustive vacancy inventory"


def _parse_date(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    for parser in (lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")), parsedate_to_datetime):
        try:
            dt = parser(value)
            return dt.date().isoformat()
        except (ValueError, TypeError, IndexError, OverflowError):
            continue
    return None


def _news(pb: ProfileBuilder, fetcher: Fetcher, visit: SiteVisit, origin: str, max_items: int = 8) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=730)).date().isoformat()
    today = datetime.now(timezone.utc).date().isoformat()
    items: list[tuple[str, str, str, Page, str]] = []
    publisher_fragments: dict[str, list[str]] = {}
    targets: list[str] = []
    generic = {"news", "nyheter", "aktuelt", "blog", "blogg", "see more news", "view all news", "latest news",
               "read more", "les mer", "se alle nyheter", "flere nyheter", "siste nytt", "see all news"}
    legal_name = pb.extra.get("legal_name") or next((c.value for c in pb.family_claims("identity") if c.field == "legal_name"), "")

    def same_site(url: str) -> bool:
        # Ownership is scoped to the verified host, never inherited by siblings.
        return urllib.parse.urlsplit(url).hostname == urllib.parse.urlsplit(origin).hostname

    def publication_date(value) -> str | None:
        parsed = parse_job_date(value)
        if parsed is None and isinstance(value, str):
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.utcoffset() is None:
                    return None
            except (ValueError, TypeError, OverflowError):
                return None
        if parsed is None or job_not_yet_published(parsed, datetime.now(timezone.utc)):
            return None
        return parsed.isoformat()

    def add(date: str | None, title: object, url: object, page: Page, excerpt: str) -> None:
        link = item_url(url, page.url)
        if (not date or not cutoff <= date[:10] <= today or not isinstance(title, str) or len(title.strip()) < 8
                or fold(title.strip()) in generic or not link or not same_site(link) or not single_item_url(link, "news")):
            return
        path = fold(urllib.parse.urlsplit(link).path)
        if re.search(r"/(products?|produkter|shop|butikk|services?|tjenester|careers|jobs)/", path):
            return
        if link != item_url(page.url, page.url):
            targets.append(link)
            return  # a listing card is discovery; fetch the actual post before publication
        if excerpt and len(excerpt) <= 600:
            items.append((date, title.strip()[:200], link, page, excerpt))

    def from_page(page: Page) -> None:
        if not same_site(page.url):
            return
        if not in_verified_scope(page, visit, pb.org, legal_name):
            pb.extra.setdefault("news_rejections", []).append({"url": page.url, "reason_code": "identity_unproven"})
            return
        article_nodes = [n for n in page.jsonld if schema_types(n) & {"NewsArticle", "BlogPosting", "Article"}]
        relevant = [n for n in article_nodes if item_url(n.get("url") or page.url, page.url) == item_url(page.url, page.url)]
        if any(n.get("publisher") and not _employer_matches(_resolved_publisher(page, n["publisher"]), pb.org, legal_name) for n in relevant):
            pb.trace_discovery("news", page.url, page.url, "publisher_conflict")
            pb.error("activity", "article publisher conflicts with the exact company", page.url)
            return
        for node in relevant:
            original = node.get("publisher")
            resolved = _resolved_publisher(page, original)
            if isinstance(original, dict) and original.get("@id") and resolved is not original:
                proof = {"@id": resolved["@id"], **_organization_excerpt(resolved)}
                # Retain the source graph node separately, never invent nested identity fields.
                reference = json.dumps({"publisher": original}, ensure_ascii=False)
                definition = json.dumps(proof, ensure_ascii=False)
                if len(reference) > 600 or len(definition) > 600:
                    return
                publisher_fragments.setdefault(page.url, []).extend([reference, definition])
        if not article_page(page):
            # Structured listing cards may still discover an article detail.
            for node in article_nodes:
                url = item_url(node.get("url"), page.url)
                if url and url != item_url(page.url, page.url) and same_site(url) and single_item_url(url, "news"):
                    targets.append(url)
            pb.extra.setdefault("news_rejections", []).append({"url": page.url, "reason_code": "not_article"})
            return
        for node in page.jsonld:
            if not schema_types(node) & {"NewsArticle", "BlogPosting", "Article"}:
                continue
            publisher = _resolved_publisher(page, node.get("publisher"))
            if publisher and not _employer_matches(publisher, pb.org, legal_name):
                continue
            title_field = "headline" if node.get("headline") else "name"
            proof = {key: node[key] for key in (title_field, "datePublished") if key in node}
            if publisher:
                publisher_excerpt = _organization_excerpt(publisher)
                if not _employer_matches(publisher_excerpt, pb.org, legal_name):
                    continue
                proof["publisher"] = node["publisher"] if node["publisher"].get("@id") else publisher_excerpt
            add(publication_date(node.get("datePublished")), node.get("headline") or node.get("name"),
                node.get("url") or page.url, page, json.dumps(proof, ensure_ascii=False))
        if page.doc is None:
            return
        headings = page.doc.xpath("//main//h1|//article//h1")
        if len(headings) == 1:
            # Some releases keep the displayed date in a sibling of the label.
            heading = " ".join(headings[0].text_content().split())
            for label in headings[0].getparent().xpath("./aside/*[not(*)]"):
                day = label.getnext()
                if (fold(label.text_content()).strip() not in {"published:", "publisert:"}
                        or day is None or day.tag not in {"div", "span", "time", "p"} or len(day)):
                    continue
                parsed = vacancy_day(day.text_content())
                if parsed:
                    excerpt = etree.tostring(label, encoding="unicode", method="html") + etree.tostring(
                        day, encoding="unicode", method="html", with_tail=False)
                    add(publication_date(parsed.isoformat()), heading, page.url, page, excerpt)
            # CMS pages sometimes expose the publication date as a labelled line.
            # Bind a visible date to the headline block. Related cards on an undated
            # article can carry their own genuine publication dates.
            for el in headings[0].getparent().xpath("./*[not(*) and not(self::a)]"):
                line = " ".join((el.text or "").split())
                match = re.fullmatch(r"(?:published|publisert)\s*:\s*(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})", line, re.I)
                if match:
                    raw = match[1]
                    iso = "-".join(reversed(raw.split("."))) if "." in raw else raw
                    add(publication_date(iso), headings[0].text_content().strip(), page.url, page,
                        etree.tostring(el, encoding="unicode", method="html", with_tail=False))
        # Only an explicit publication date, never an unlabelled time or dateModified.
        date = publication_date(page.meta.get("article:published_time"))
        if date:
            heads = page.doc.xpath("//article//h1|//main//h1|//h1")
            title = " ".join(heads[0].text_content().split()) if heads else page.meta.get("og:title")
            date_meta = next((m for m in page.doc.iter("meta")
                              if (m.get("property") or m.get("name") or "").lower() == "article:published_time"
                              and publication_date(m.get("content")) == date), None)
            if date_meta is not None:
                add(date, title, page.url, page, etree.tostring(date_meta, encoding="unicode", method="html", with_tail=False))
        for art in page.doc.xpath("//article")[:20]:
            times = art.xpath(".//time[@datetime]")
            for t in times:
                marker = fold(" ".join([t.get("itemprop", ""), t.get("class", ""), t.get("pubdate", ""), t.text_content()]))
                context = fold(t.getparent().text_content()) if t.getparent() is not None else marker
                if (re.search(r"\b(?:modified|datemodified|updated|unpublished|not published)\b", marker)
                        or re.search(r"\b(?:oppdatert|ikke publisert|not published)\b", context)):
                    continue
                explicit_marker = bool(re.search(r"\b(?:datepublished|published)\b", marker)) or t.get("pubdate") is not None
                if not explicit_marker and not re.search(r"\bpublisert\b", context):
                    continue
                heads = art.xpath(".//h1|.//h2|.//h3")
                title = " ".join(heads[0].text_content().split()) if heads else ""
                links = heads[0].xpath(".//a[@href]") if heads else []
                date_element = t if explicit_marker else t.getparent()
                add(publication_date(t.get("datetime")), title, links[0].get("href") if links else page.url, page,
                    etree.tostring(date_element, encoding="unicode", method="html", with_tail=False))

    for page in visit.pages:
        from_page(page)
    home = visit.pages[0]
    # News feeds are discovery hints. Verify each target as an actual article; product feeds do not qualify.
    sources = {}
    try:
        feeds = [f for f in home.feeds if same_site(f) and "comments" not in f]
        if feeds:
            snap = fetcher.get(feeds[0], phase="web_news", max_bytes=1_500_000)
            if snap.ok and same_site(snap.final_url):
                try:
                    root = etree.fromstring(snap.body, parser=etree.XMLParser(resolve_entities=False, no_network=True))
                except etree.XMLSyntaxError:
                    root = None
                if root is not None:
                    for it in root.iter():
                        if not isinstance(it.tag, str) or etree.QName(it).localname not in {"item", "entry"}:
                            continue
                        date = publication_date(it.findtext("pubDate") or it.findtext("{*}published"))
                        if not date or not cutoff <= date[:10] <= today:
                            continue
                        links = [el for el in it if isinstance(el.tag, str) and etree.QName(el).localname == "link" and el.get("rel", "alternate") == "alternate"]
                        if links:
                            url = item_url(links[0].get("href") or links[0].text, snap.final_url)
                            if url and same_site(url):
                                targets.append(url)
                                sources.setdefault(url, snap.final_url)
        for p in visit.pages:
            if not in_verified_scope(p, visit, pb.org, legal_name):
                continue
            for u, txt in p.links:
                if item_url(u, p.url) and same_site(u) and NEWS_HINTS.search(fold(urllib.parse.urlsplit(u).path + " " + txt)):
                    targets.append(u)
                    sources.setdefault(u, p.url)
        # Prioritize individual releases ahead of generic investor navigation.
        targets.sort(key=lambda u: not (single_item_url(u, "news") and re.search(
            r"/(?:borsmelding|press-releases?|news|nyheter)/[^/]+", fold(urllib.parse.urlsplit(u).path))))
        def discover_maps():
            host = urllib.parse.urlsplit(home.url).hostname
            maps = [item_url(u, home.url) for u, _ in home.links
                    if re.search(r"(?:^|/)sitemap[^/]*\.xml$", urllib.parse.urlsplit(u).path, re.I)]
            maps.extend(getattr(fetcher, "sitemap_urls", lambda _: [])(home.url))
            visited_maps = set()
            while maps and len(visited_maps) < 2 and len(targets) < 3:
                url = maps.pop(0)
                if not url or url in visited_maps or urllib.parse.urlsplit(url).hostname != host:
                    continue
                visited_maps.add(url)
                snap = fetcher.get(url, phase="web_news", max_bytes=500_000)
                if not snap.ok or urllib.parse.urlsplit(snap.final_url).hostname != host:
                    continue
                try:
                    root = etree.fromstring(snap.body, parser=etree.XMLParser(resolve_entities=False, no_network=True))
                except etree.XMLSyntaxError:
                    continue
                if root.getroottree().docinfo.doctype:
                    continue
                kind = etree.QName(root).localname
                if kind == "sitemapindex":
                    maps.extend(item_url(value, snap.final_url) for value in root.xpath("./*/s:loc/text()",
                                namespaces={"s": "http://www.sitemaps.org/schemas/sitemap/0.9"})[:20])
                elif kind == "urlset":
                    for value in root.xpath("./*/*[local-name()='loc']/text()"):
                        link = item_url(value, snap.final_url)
                        if (link and urllib.parse.urlsplit(link).hostname == host and single_item_url(link, "news")
                                and NEWS_HINTS.search(urllib.parse.urlsplit(link).path) and link not in targets):
                            targets.append(link)
                            sources.setdefault(link, snap.final_url)
                        if len(targets) >= 3:
                            break
        seen_pages = {p.url for p in visit.pages}
        fetched = 0
        maps_tried = False
        while fetched < 3:
            if not targets:
                if maps_tried or items:
                    break
                maps_tried = True
                discover_maps()
                if not targets:
                    break
            url = targets.pop(0)
            if url in seen_pages:
                continue
            seen_pages.add(url)
            snap = fetcher.get(url, phase="web_news")
            fetched += 1
            pb.trace_discovery("news", sources.get(url, home.url), url, "fetched" if snap.ok else "fetch_failed")
            if not snap.ok or not same_site(snap.final_url):
                continue
            page = Page(snap)
            from_page(page)
            if not single_item_url(page.url, "news") and in_verified_scope(page, visit, pb.org, legal_name):
                children = [u for u, _ in page.links if item_url(u, page.url) and same_site(u)
                            and NEWS_HINTS.search(urllib.parse.urlsplit(u).path) and single_item_url(u, "news")]
                # Article-card links need not contain /news/ in their slug.
                if page.doc is not None:
                    cards = [item_url(a.get("href"), page.url) for a in page.doc.xpath(
                        "//article//h2/a[@href]|//article//h3/a[@href]|//main//h2/a[@href]|//main//h3/a[@href]")
                        if item_url(a.get("href"), page.url) and same_site(item_url(a.get("href"), page.url))
                        and single_item_url(item_url(a.get("href"), page.url), "news")]
                    children = cards + children
                for child in children:
                    sources[child] = page.url
                targets[:0] = list(dict.fromkeys(children))
    except BudgetExhausted:
        pb.extra.setdefault("incomplete_families", {})["activity"] = "news request budget exhausted"
    seen: set[str] = set()
    for date, title, url, page, excerpt in sorted(items, key=lambda x: x[0], reverse=True):
        if url in seen:
            continue
        seen.add(url)
        pb.trace_discovery("news", sources.get(url, home.url), url, "published")
        ev = pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at, page.snap.sha256, excerpt,
                                      "article:explicit_publication_date", identity_reason="dated article on the verified company website",
                                      reporting_period={"from": date, "to": date}))
        evidence_ids = [ev]
        for fragment in dict.fromkeys(publisher_fragments.get(page.url, [])):
            evidence_ids.append(pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at,
                                                        page.snap.sha256, fragment, "article:publisher_graph")))
        if excerpt.startswith("<"):
            evidence_ids.append(pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at,
                                                          page.snap.sha256, title, "article:headline")))
        evidence_ids.extend(eid for claim in pb.family_claims("website") if claim.field == "official_website"
                            for eid in claim.evidence_ids)
        pb.add(Claim("activity", "company_news", {"title": title, "url": url, "date": date}, evidence_ids,
                     label="Company news / post (company-owned)", effective_date=date, key=f"news:{url}"))
        if len(seen) >= max_items:
            break


def research_website(pb: ProfileBuilder, fetcher: Fetcher, entity: dict, bulk_row: dict | None, related_orgs: set[str], *,
                     max_candidates: int = 4, want_news: bool = True, defer_enrichment: bool = False,
                     candidates: list[tuple[str, str]] | None = None) -> None:
    legal_name = entity.get("navn") or (bulk_row or {}).get("navn") or ""
    cands = candidates if candidates is not None else domain_candidates(entity, bulk_row, pb.extra.get("site_candidates"))
    diag = pb.extra.setdefault("website_diagnostics", {"attempts": [], "candidate_urls": [], "budget_interruptions": 0})
    diag["candidate_urls"] = list(dict.fromkeys(diag["candidate_urls"] + [u for u, _ in cands]))
    pb.extra["website_pending_candidates"] = list(cands)
    if not cands:
        if diag["attempts"]:
            return  # retain the result of a completed first-round check
        pb.set_state("website", "not_available", "registry lists no website or company e-mail domain, and no name-based domain resolves")
        for fam in ("social_profiles", "description", "contact"):
            pb.set_state(fam, "not_available", "no verified official website to read from")
        return
    decisions = [a["decision"] for a in diag["attempts"] if a["completed"]]
    accepted: SiteVisit | None = None
    for candidate, source in cands[:max_candidates]:
        attempt = {"candidate": candidate, "source": source, "decision": "budget", "completed": False}
        diag["attempts"].append(attempt)
        try:
            people = {t for c in pb.family_claims("leadership") for t in name_tokens(str(c.value))}
            visit = visit_site(fetcher, candidate, source, pb.org, {**entity, "_unit_emails": pb.extra.get("emails", [])}, legal_name,
                               related_orgs, person_tokens=people)
        except BudgetExhausted:
            diag["budget_interruptions"] += 1
            decisions.append("budget")
            break
        attempt.update(decision=visit.decision, completed=visit.decision != "budget", reason=visit.reason)
        if visit.decision == "budget":
            diag["budget_interruptions"] += 1
            decisions.append("budget")
            break
        pb.extra["website_pending_candidates"].remove((candidate, source))
        decisions.append(visit.decision)
        if visit.decision == "accepted":
            accepted = visit
            break
        pb.candidates.append({"family": "website", "candidate": candidate, "source": source, "decision": visit.decision,
                              "decision_code": visit.decision_code, "reason": visit.reason})
        if visit.decision == "related_site":
            rel_page = visit.pages[0]
            ev = pb.add_evidence(Evidence(rel_page.url, "company_owned", rel_page.snap.retrieved_at, rel_page.snap.sha256,
                                          _span_around(rel_page.text, r"(?i)org") or rel_page.title, "identity_gate:related_site", identity_reason=visit.reason))
            pb.add(Claim("group", "related_website", visit.origin, [ev], label="Website of a related group entity (labelled, not the company's own)",
                         key=f"related_site:{registrable_domain(visit.origin)}", confidence=0.9))
    if accepted:
        pb.extra["website_pending_candidates"] = []
        try:
            extract_company_owned(pb, fetcher, accepted, legal_name, want_news=want_news, defer_enrichment=defer_enrichment)
        except BudgetExhausted:
            pass
        return
    if "budget" in decisions and not any(d in ("ambiguous", "rejected", "related_site") for d in decisions):
        pb.set_state("website", "failed", "request budget exhausted before the website check completed")
    elif any(d in ("ambiguous", "rejected", "related_site") for d in decisions):
        pb.set_state("website", "ambiguous", "candidate site(s) found but none passed the exact-entity identity gate")
    elif "blocked" in decisions:
        pb.set_state("website", "blocked", "robots.txt disallows access to the candidate site")
    else:
        pb.set_state("website", "not_available", "candidate domains were unreachable")
    for fam in ("social_profiles", "description", "contact"):
        state = pb.families["website"].state
        pb.set_state(fam, state if state in {"failed", "blocked", "ambiguous"} else "not_available",
                     "no verified official website to read from: " + pb.families["website"].reason)
