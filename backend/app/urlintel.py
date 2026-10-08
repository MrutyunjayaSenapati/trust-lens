"""Turn a pasted link into something we can investigate, using SerpApi (never by scraping the page itself).

LinkedIn, Naukri and most shops block scrapers, but Google has already indexed their titles and snippets, so one
SerpApi google search on the URL tells us who is hiring, for what role, where, or what product is being sold.

Brand-new postings are not indexed yet. Job sites often put the role and company in the URL itself
(/jobs/view/full-stack-engineer-at-accenture-in-india-4474509677, /job-listings-...), so those words are used as a
fallback. A bare /jobs/view/<id> link carries no such words; the user is asked to paste the posting text instead.
"""
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import unquote, urlparse

from .serp import SerpClient
from .util import domain_of

URL_RE = re.compile(r"(?:https?://|www\.)[^\s)>\]]+", re.I)
LINKEDIN_JOB_RE = re.compile(r"linkedin\.com/jobs/view/(?:[^/?\s]*-)?(\d{6,})", re.I)
# "Acme Corp hiring Software Engineer in Bengaluru, Karnataka, India | LinkedIn"
HIRING_RE = re.compile(r"^(?P<company>.+?)\s+hiring\s+(?P<role>.+?)(?:\s+in\s+(?P<city>[^|\-]+?))?\s*(?:\||$|-\s*LinkedIn)", re.I)
# "Software Engineer - Acme Corp - Bengaluru | Naukri / Indeed / Glassdoor"
DASH_RE = re.compile(r"^(?P<role>.+?)\s+[-–|]\s+(?P<company>.+?)\s+[-–|]\s+(?P<city>[^|\-]+?)(?:\s*[|\-].*)?$")

# Enterprise applicant-tracking systems that host a company's own careers pages (sales-led, no self-serve free
# accounts, unlike Workable or Zoho Recruit trials). The account name is in the URL: a path segment
# (jobs.lever.co/wahed.com/...) or a subdomain (acme.wd3.myworkdayjobs.com, acme.keka.com).
ATS_PATH_HOSTS = ("jobs.lever.co", "boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.ashbyhq.com",
                  "jobs.smartrecruiters.com")
ATS_SUBDOMAIN_HOSTS = ("myworkdayjobs.com", "keka.com", "darwinbox.in")
JOB_HOSTS = ("linkedin.com", "naukri.com", "indeed.com", "internshala.com", "foundit.in", "glassdoor", "instahyre", "wellfound",
             "apna.co", "shine.com") + ATS_PATH_HOSTS + ATS_SUBDOMAIN_HOSTS
SHOP_HOSTS = ("amazon.", "flipkart.com", "myntra.com", "meesho.com", "snapdeal.com", "ajio.com", "olx.in", "tatacliq.com")
EXPERIENCE_RE = re.compile(r"\b\d+\s*(?:-|to)\s*\d+\s*(?:yrs?|years?)\b|\b\d+\+?\s*(?:yrs?|years?)\b|\bfresher\b", re.I)
# /jobs/view/full-stack-engineer-at-accenture-in-india-4474509677
LINKEDIN_SLUG_RE = re.compile(r"/jobs/view/(?P<role>[a-z0-9-]+?)-at-(?P<company>[a-z0-9-]+?)-\d{6,}", re.I)
# /job-listings-software-engineer-acme-technologies-pvt-ltd-bengaluru-3-to-5-years-081024012345
NAUKRI_SLUG_RE = re.compile(r"/job-listings-(?P<words>[a-z0-9-]+?)-\d{9,}", re.I)


@dataclass
class Resolved:
    url: str
    title: str = ""
    snippet: str = ""
    company: Optional[str] = None
    role: Optional[str] = None
    city: Optional[str] = None
    kind: str = "other"
    link: str = ""
    url_words: str = ""  # role/company words found in the URL itself, for postings Google has not indexed yet
    on_job_site: bool = False
    ats_host: str = ""  # e.g. jobs.lever.co
    ats_account: str = ""  # the company's account on it, e.g. wahed.com

    @property
    def found(self) -> bool:
        return bool(self.title)


def find_url(text: str) -> Optional[str]:
    m = URL_RE.search(text or "")
    return m.group(0).rstrip(".,;") if m else None


def is_link_only(text: str) -> bool:
    """True when the submission is essentially just a link (nothing else to analyse)."""
    url = find_url(text)
    return bool(url) and len(URL_RE.sub("", text).strip()) < 40


def _parse_title(title: str, host: str) -> dict:
    t = re.sub(r"\s*\|\s*(LinkedIn|Naukri\.com|Indeed|Internshala|Glassdoor).*$", "", title, flags=re.I).strip()
    m = HIRING_RE.match(title)
    if m:
        return {"company": m.group("company").strip(), "role": m.group("role").strip(),
                "city": (m.group("city") or "").split(",")[0].strip() or None}
    if any(h in host for h in JOB_HOSTS):
        # "Software Engineer - Acme Technologies - 3-5 Yrs - Bengaluru": drop the experience part before splitting
        parts = [p.strip() for p in re.split(r"\s+[-–|]\s+", t) if p.strip() and not EXPERIENCE_RE.fullmatch(p.strip())]
        if len(parts) >= 3:  # two parts are ambiguous ("Full Stack Engineer - Greater Kolkata Area"), so not used
            return {"role": parts[0], "company": parts[1], "city": parts[-1].split(",")[0].strip()}
    return {}


# Query parameters that identify the posting; everything else (tracking, referrer, session) is dropped before
# searching, because a click-specific URL can never match what Google indexed.
KEEP_PARAMS = {"jk", "id", "jobid", "job_id", "gh_jid", "currentjobid"}


def canonical_url(url: str) -> str:
    p = urlparse(url if "//" in url else "//" + url)
    keep = [kv for kv in p.query.split("&") if kv and kv.split("=", 1)[0].lower() in KEEP_PARAMS]
    return p._replace(query="&".join(keep), fragment="").geturl()


def _words(slug: str) -> str:
    return re.sub(r"\s+", " ", unquote(slug).replace("-", " ")).strip()


def ats_account(url: str) -> dict:
    """{'ats_host', 'ats_account'} when the link is a company's page on a recruiting system."""
    p = urlparse(url if "//" in url else "//" + url)
    host = (p.hostname or "").lower()
    for h in ATS_PATH_HOSTS:
        if host == h:
            seg = next((s for s in p.path.split("/") if s), "")
            return {"ats_host": h, "ats_account": unquote(seg).lower()} if seg else {}
    for h in ATS_SUBDOMAIN_HOSTS:
        if host.endswith("." + h):
            sub = host[: -len(h) - 1].split(".")[0]  # acme.wd3.myworkdayjobs.com -> acme
            return {"ats_host": h, "ats_account": sub} if sub not in ("www", "careers", "jobs") else {}
    return {}


def url_hints(url: str) -> dict:
    """Role/company words that job sites put in the URL itself. Free: no request is made."""
    m = LINKEDIN_SLUG_RE.search(url)
    if m:
        return {"role": _words(m.group("role")).title(), "company": _words(m.group("company")).title(),
                "url_words": f"{_words(m.group('role'))} at {_words(m.group('company'))}"}
    m = NAUKRI_SLUG_RE.search(url)
    if m:  # no separator between role, company and city: hand the words to extraction (Gemini, then regex)
        return {"url_words": EXPERIENCE_RE.sub("", _words(m.group("words").replace("-to-", " to "))).strip()}
    return {}


async def resolve(url: str, serp: SerpClient) -> Resolved:
    full = canonical_url(url if url.lower().startswith("http") else "https://" + url)
    host = domain_of(full)
    out = Resolved(url=full, on_job_site=any(h in host for h in JOB_HOSTS))
    queries = []
    job_id = LINKEDIN_JOB_RE.search(full)
    for k, v in {**url_hints(full), **ats_account(full)}.items():
        setattr(out, k, v)
    if out.on_job_site:
        out.kind = "job_offer"
    if job_id:
        queries.append(f"linkedin.com/jobs/view/{job_id.group(1)}")
    queries.append(full)
    for q in queries:
        data = await serp.search("google", q=q, gl="in", hl="en", num=10)
        for r in data.get("organic_results", []):
            link = r.get("link", "")
            same = domain_of(link) == host or (job_id and job_id.group(1) in link)
            if not same:
                continue
            out.title, out.snippet, out.link = r.get("title", ""), r.get("snippet", ""), link
            break
        if out.title:
            break
    if not out.title:
        return out
    for k, v in _parse_title(out.title, host).items():  # Google's indexed title beats words guessed from the URL
        setattr(out, k, v)
    if not out.on_job_site and any(h in host for h in SHOP_HOSTS):
        out.kind = "deal"
    return out
