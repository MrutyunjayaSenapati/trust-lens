import re
from typing import Optional
from urllib.parse import urlparse

GENERIC = {
    "pvt", "ltd", "limited", "private", "solutions", "technologies", "technology", "global",
    "services", "india", "inc", "llp", "corp", "company", "systems", "group", "the", "and",
    "consulting", "enterprises", "international", "infotech", "software", "corporation",
}
LEGAL = {"pvt", "ltd", "limited", "private", "llp", "inc", "corp", "corporation", "co", "plc"}
# second-level suffixes, so "acme.co.in" -> label "acme"
MULTI_TLD = ("co.in", "org.in", "net.in", "firm.in", "gen.in", "ind.in", "co.uk", "com.au")
# a company's own alternate domains look like "<brand><one of these>" (zohocorp.com, acmeindia.in)
# (kept short on purpose: "careers", "jobs", "hr" tails are what impersonators register)
ALT_DOMAIN_TAILS = ("", "corp", "group", "inc", "india", "hq")
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


def clean_company(company: str) -> str:
    """'Wipro Limited' -> 'Wipro'. Legal suffixes add nothing to a search and can drown it ('Limited' -> dictionaries)."""
    words = (company or "").split()
    while len(words) > 1 and re.sub(r"[^a-z]", "", words[-1].lower()) in LEGAL:
        words.pop()
    return " ".join(words)


def acronym(company: str) -> str:
    """'Tata Consultancy Services' -> 'tcs'. Only for multi-word names."""
    words = [w for w in tokens(company) if w not in LEGAL]
    return "".join(w[0] for w in words) if len(words) >= 2 else ""


def domain_label(domain: str) -> str:
    """Registrable label of a domain: 'careers.acme.co.in' -> 'acme'."""
    d = (domain or "").lower().strip(".")
    for suf in MULTI_TLD:
        if d.endswith("." + suf):
            d = d[: -len(suf) - 1]
            break
    else:
        d = d.rsplit(".", 1)[0] if "." in d else d
    return d.rsplit(".", 1)[-1]


def domain_contains_company(domain: str, company: str) -> bool:
    d = re.sub(r"[^a-z0-9]", "", domain.split(":")[0])
    need = sig_tokens(company)
    if need and all(t in d for t in need[:2]):
        return True
    ac = acronym(company)
    return len(ac) >= 3 and domain_label(domain) == ac


def is_alt_domain(sender: str, official: str) -> bool:
    """True when the sender's domain is plausibly the company's own alternate domain (swiggy.in vs swiggy.com,
    zohocorp.com vs zoho.com). Look-alikes such as infosys-careers.co.in or tcs-careerhub.co.in do not qualify."""
    s, o = domain_label(sender), domain_label(official)
    return bool(s and o) and s.startswith(o) and s[len(o):] in ALT_DOMAIN_TAILS
