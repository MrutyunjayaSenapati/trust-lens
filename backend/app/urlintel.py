"""Turn a pasted link into something we can investigate, using SerpApi (never by scraping the page itself).

LinkedIn, Naukri and most shops block scrapers, but Google has already indexed their titles and snippets, so one
SerpApi google search on the URL tells us who is hiring, for what role, where, or what product is being sold.
"""
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from .serp import SerpClient
from .util import domain_of

URL_RE = re.compile(r"(?:https?://|www\.)[^\s)>\]]+", re.I)
LINKEDIN_JOB_RE = re.compile(r"linkedin\.com/jobs/view/(?:[^/?\s]*-)?(\d{6,})", re.I)
# "Acme Corp hiring Software Engineer in Bengaluru, Karnataka, India | LinkedIn"
HIRING_RE = re.compile(r"^(?P<company>.+?)\s+hiring\s+(?P<role>.+?)(?:\s+in\s+(?P<city>[^|\-]+?))?\s*(?:\||$|-\s*LinkedIn)", re.I)
# "Software Engineer - Acme Corp - Bengaluru | Naukri / Indeed / Glassdoor"
DASH_RE = re.compile(r"^(?P<role>.+?)\s+[-–|]\s+(?P<company>.+?)\s+[-–|]\s+(?P<city>[^|\-]+?)(?:\s*[|\-].*)?$")

JOB_HOSTS = ("linkedin.com", "naukri.com", "indeed.com", "internshala.com", "foundit.in", "glassdoor", "instahyre", "wellfound", "apna.co", "shine.com")
SHOP_HOSTS = ("amazon.", "flipkart.com", "myntra.com", "meesho.com", "snapdeal.com", "ajio.com", "olx.in", "tatacliq.com")


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
    m = DASH_RE.match(t)
    if m and any(h in host for h in JOB_HOSTS):
        return {"company": m.group("company").strip(), "role": m.group("role").strip(), "city": m.group("city").split(",")[0].strip()}
    return {}


async def resolve(url: str, serp: SerpClient) -> Resolved:
    full = url if url.lower().startswith("http") else "https://" + url
    host = domain_of(full)
    out = Resolved(url=full)
    queries = []
    job_id = LINKEDIN_JOB_RE.search(full)
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
    for k, v in _parse_title(out.title, host).items():
        setattr(out, k, v)
    if any(h in host for h in JOB_HOSTS):
        out.kind = "job_offer"
    elif any(h in host for h in SHOP_HOSTS):
        out.kind = "deal"
    return out
