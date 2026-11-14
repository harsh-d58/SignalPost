"""Bounded discovery through Greenhouse's documented public GET API.

Only follow a board explicitly linked by an exact-company page. Board names and
updated_at are never employer identity or publication-date evidence.
"""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .budget import BudgetExhausted
from .job_dates import parse_job_date, job_expired, job_not_yet_published
from .model import Claim, Evidence

BOARD_HOSTS = {"boards.greenhouse.io", "job-boards.greenhouse.io"}
DOCS = "https://docs.greenhouse.io/job-board.html"


def greenhouse_jobs(pb, fetcher, pages, legal_name):
    from .web import _employer_matches, page_attributed
    candidates = {}
    for page in pages:
        if not page_attributed(page, pb.org, legal_name):
            continue
        for url, _ in page.links:
            parsed = urlsplit(url)
            parts = parsed.path.strip("/").split("/")
            if (parsed.scheme == "https" and parsed.hostname in BOARD_HOSTS and not parsed.username
                    and re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", parts[0])):
                candidates.setdefault(parts[0], (page, url))
    for board, (page, link) in list(candidates.items())[:1]:
        base = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        try:
            listing = fetcher.get_json(base, phase="web_news", retries=0)
            if not listing.ok:
                continue
            data = listing.json()
            rows = data.get("jobs", []) if isinstance(data, dict) else []
            if not isinstance(rows, list):
                continue
            ids = list(dict.fromkeys(r["id"] for r in rows if isinstance(r, dict)
                                    and type(r.get("id")) is int and r["id"] > 0
                                    and type(r.get("internal_job_id")) is int))[:2]
            for job_id in ids:
                snap = fetcher.get_json(f"{base}/{job_id}", phase="web_news", retries=0)
                if not snap.ok:
                    continue
                job = snap.json()
                if not isinstance(job, dict) or type(job.get("id")) is not int or job["id"] != job_id:
                    continue
                reason = None
                posted = parse_job_date(job.get("first_published"))
                deadline = parse_job_date(job.get("application_deadline"))
                now = datetime.now(timezone.utc)
                if not _employer_matches({"name": job.get("company_name")}, pb.org, legal_name):
                    reason = "wrong_employer"
                elif not posted or job_not_yet_published(posted, now):
                    reason = "missing_or_invalid_publication_date"
                elif job.get("application_deadline") and (not deadline or job_expired(deadline, now)):
                    reason = "expired_or_invalid_deadline"
                elif not isinstance(job.get("title"), str) or not job["title"].strip():
                    reason = "missing_title"
                if reason:
                    pb.extra.setdefault("job_rejections", []).append({"url": snap.url, "reason_code": reason})
                    continue
                # Use the documented hosted detail route for this exact API ID;
                # never publish an arbitrary API-supplied landing/search URL.
                url = f"https://boards.greenhouse.io/{board}/jobs/{job_id}"
                proof = {k: job[k] for k in ("id", "company_name", "title", "first_published", "application_deadline") if k in job}
                span = json.dumps(proof, ensure_ascii=False)
                if len(span) > 600:
                    continue
                source = pb.add_evidence(Evidence(snap.url, "public_api", snap.retrieved_at, snap.sha256,
                    span, "greenhouse:published_job", license=DOCS,
                    identity_reason="API company_name equals full legal name; exact job ID remains published"))
                discovery = pb.add_evidence(Evidence(page.url, "company_owned", page.snap.retrieved_at,
                    page.snap.sha256, link, "html_link:greenhouse_board"))
                value = {"title": job["title"].strip(), "employer": legal_name, "url": url,
                         "published": posted.isoformat(), "source": "Greenhouse public Job Board API"}
                if deadline:
                    value["expires"] = deadline.isoformat()
                pb.add(Claim("jobs", "job_posting", value, [source, discovery],
                             label="Active job posting", key=f"greenhouse:{board}:{job_id}", effective_date=posted.isoformat()))
                pb.set_state("jobs", "available", "exact-employer dated published Greenhouse job", snap.url)
        except BudgetExhausted:
            pb.extra.setdefault("job_rejections", []).append({"url": base, "reason_code": "budget_unattempted"})
        except (ValueError, TypeError):
            pb.extra.setdefault("job_rejections", []).append({"url": base, "reason_code": "invalid_api_payload"})
