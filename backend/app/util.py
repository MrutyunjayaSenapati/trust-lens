import re
from typing import Optional
from urllib.parse import urlparse

GENERIC = {
    "pvt", "ltd", "limited", "private", "solutions", "technologies", "technology", "global",
    "services", "india", "inc", "llp", "corp", "company", "systems", "group", "the", "and",
    "consulting", "enterprises", "international", "infotech", "software",
}
ADDR_STOP = {
    "the", "and", "near", "opp", "opposite", "behind", "floor", "road", "rd", "street", "st",
    "no", "nr", "off", "main", "block", "sector", "phase", "india", "of", "in", "at", "flat",
}
FREE_EMAIL = {
    "gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com", "rediffmail.com",
    "proton.me", "protonmail.com", "live.com", "icloud.com", "ymail.com", "aol.com",
}


def tokens(s: str) -> list:
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def sig_tokens(company: str) -> list:
    t = [x for x in tokens(company) if x not in GENERIC and len(x) > 1]
    return t or tokens(company)


def name_match(candidate: str, company: str, threshold: float = 0.6) -> bool:
    need = sig_tokens(company)
    if not need:
        return False
    have = set(tokens(candidate))
    hit = sum(1 for t in need if t in have or any(h.startswith(t) for h in have))
    return hit / len(need) >= threshold


def domain_of(url: str) -> str:
    try:
        host = urlparse(url if "//" in url else "//" + url).netloc.lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def email_domain(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].lower().strip(" .,;)")


def addr_overlap(claimed: str, found: str) -> float:
    a = {t for t in tokens(claimed) if t not in ADDR_STOP and len(t) > 2}
    b = set(tokens(found))
    if not a:
        return 1.0
    return len([t for t in a if t in b]) / len(a)


def domain_contains_company(domain: str, company: str) -> bool:
    d = re.sub(r"[^a-z0-9]", "", domain.split(":")[0])
    need = sig_tokens(company)
    return bool(need) and all(t in d for t in need[:2])
