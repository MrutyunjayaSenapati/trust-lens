"""Cross-source reasoning: judgments that only make sense once every engine has answered."""
import re
from collections import Counter
from typing import Any, Dict, List

from .models import Contradiction, Entities, Evidence, Source
from .util import FREE_EMAIL, acronym, domain_label, email_domain, is_alt_domain, sig_tokens

# Total Google Maps reviews across a company's own listings above which it counts as an established business.
# Fake recruiters' "companies" have none or a handful; Infosys, Swiggy, Zerodha have thousands.
ESTABLISHED_REVIEWS = 100


def established(facts: Dict[str, Any]) -> bool:
    return int(facts.get("maps_reviews") or 0) >= ESTABLISHED_REVIEWS


def alt_domain_ok(ent: Entities, facts: Dict[str, Any]) -> bool:
    """Sender writes from the company's own alternate domain (swiggy.in for swiggy.com), and the web knows that domain."""
    ed, off = email_domain(ent.contact_email), facts.get("official_domain") or ""
    return (bool(ed and off) and is_alt_domain(ed, off) and int(facts.get("sender_domain_results") or 0) > 0
            and not facts.get("sender_domain_reports"))


def _official_from_maps(ent: Entities, facts: Dict[str, Any], evidence: List[Evidence]) -> None:
    """Search does not always surface the official site ("Wipro official website" returned job boards and a different
    company, wiproferretto.com). When the company's own Maps listings agree on a domain that IS the company name,
    that domain is the official site."""
    if not ent.company:
        return
    exact = {"".join(sig_tokens(ent.company)), acronym(ent.company)} - {""}
    sites = Counter(p["website"] for p in facts.get("maps_places") or [] if p["website"] and domain_label(p["website"]) in exact)
    if not sites:
        return
    site = sites.most_common(1)[0][0]
    off = facts.get("official_domain") or ""
    if off and domain_label(off) in exact:
        return  # search already found a convincing one
    facts["official_domain"] = site
    facts["official_domains"] = [site, *(facts.get("official_domains") or [])]
    for ev in evidence:
        if ev.id == "google-10":
            ev.title, ev.signal, ev.weight = f"Official website: {site} (from the company's Maps listings)", "positive", 8
            ev.detail = (f"Web search did not surface it clearly{f' (it suggested {off})' if off else ''}, but "
                         f"{sites[site]} of the company's Google Maps listings link to {site}.")
            ev.sources = [Source(title=site, url=f"https://{site}")]
    ed = email_domain(ent.contact_email)
    if ed and (ed == site or ed.endswith("." + site)) and not facts.get("email_matches_official"):
        facts["email_matches_official"] = True
        evidence.append(Evidence(id="google-11", engine="google", title="Email domain matches the official site",
                                 detail=f"{ed} is the company's own domain.", signal="positive", weight=15))


def _check_maps_identity(facts: Dict[str, Any], evidence: List[Evidence]) -> None:
    """Keep only Maps listings that are this company. With an official domain known, a listing counts when its website
    is on that domain; reviews are summed over those (a company has many offices). If listings under the name all point
    elsewhere or nowhere, they are other businesses that share the name, and say nothing about the company."""
    off = facts.get("official_domain") or ""
    places = facts.get("maps_places") or []
    if not (off and places):
        return
    lab = domain_label(off)
    own = [p for p in places if p["website"] and (is_alt_domain(p["website"], off) or domain_label(p["website"]) in
                                                   (f"get{lab}", f"try{lab}", f"use{lab}"))]  # getpostman.com
    if own:
        facts["maps_reviews"] = sum(p["reviews"] for p in own)
        return
    facts["maps_found"], facts["maps_reviews"] = False, 0
    for ev in evidence:
        if ev.id == "google_maps-1" and ev.weight > 0:
            ev.weight, ev.signal = 0, "neutral"
            ev.title = f"Maps listings under this name look like other businesses ({ev.title.split(': ', 1)[-1]})"
            ev.detail += f" None of them links to {off}, so they are not counted as the company's office."


def ats_owned(facts: Dict[str, Any]) -> bool:
    """The posting is on a recruiting system (Lever, Greenhouse...) under an account named after the official domain."""
    acct, off = facts.get("ats_account") or "", facts.get("official_domain") or ""
    return bool(acct and off) and re.sub(r"[^a-z0-9]", "", acct.lower()) in (
        re.sub(r"[^a-z0-9]", "", off.lower()), domain_label(off))


def reconcile(ent: Entities, facts: Dict[str, Any], evidence: List[Evidence]) -> List[Evidence]:
    """Re-weigh single-engine evidence in the light of the others. Every change is written into the evidence detail,
    so the score ledger still explains each point."""
    _official_from_maps(ent, facts, evidence)
    _check_maps_identity(facts, evidence)
    if ats_owned(facts):
        evidence.append(Evidence(id="x-ats", engine="google", title=f"Posted on {facts['official_domain']}'s own hiring system",
                                 detail=f"The link is on {facts['ats_host']}, a paid recruiting platform, under the account "
                                        f"“{facts['ats_account']}”, which matches the company's official site. Scammers rarely "
                                        "operate these accounts. Apply only through this page.",
                                 signal="positive", weight=12))
    if established(facts):
        n = facts.get("maps_reviews")
        for ev in evidence:
            if ev.id in ("google-1", "google_news-1") and ev.weight < 0:
                ev.weight, ev.signal = 0, "neutral"
                ev.detail += (f" Not counted against it: this business has {n:,} Google Maps reviews, and fraud mentions of a "
                              "brand this size are mostly about scams that misuse its name. What matters is whether this "
                              "message traces back to the company.")
    if facts.get("email_matches_official"):
        for ev in evidence:  # the company's own domain is judged by the company's reputation, not by a keyword search
            if ev.id == "google-20" and ev.weight < 0:
                ev.weight, ev.signal = 0, "neutral"
    # A real brand is not evidence that a message is real. Brand-existence credit only counts when the message itself
    # traces back to the company: through its email domain, or (for a pasted link) a job-site posting that Google has
    # indexed under that company while Google Jobs independently lists the role there. Otherwise anyone could borrow
    # "Amazon" and score well.
    listing_traced = bool(facts.get("job_site_listing")) and facts.get("jobs_found") is True
    traced = facts.get("email_matches_official") or alt_domain_ok(ent, facts) or listing_traced or ats_owned(facts)
    if listing_traced:
        evidence.append(Evidence(id="x-listing", engine="google", title="Posting traces back to the company",
                                 detail=f"Google has indexed this posting on {facts['job_site_listing']} under this company, and Google Jobs "
                                        "independently lists the role there. Still apply only through the job site or the official careers page.",
                                 signal="positive", weight=0))
    if ent.kind == "job_offer" and not traced:
        for ev in evidence:
            if ev.id in ("google_maps-1", "google-10") and ev.weight > 0:
                ev.weight, ev.signal = 0, "neutral"
                ev.detail += " The brand is real, but nothing in this message ties it to the brand, so this earns no trust."
    if alt_domain_ok(ent, facts):
        ed = email_domain(ent.contact_email)
        evidence.append(Evidence(id="x-alt-domain", engine="google", title=f"{ed} looks like the company's own alternate domain",
                                 detail=f"It shares the brand name with {facts['official_domain']} and Google knows it with no scam "
                                        "reports. Confirm on the official careers page if unsure.", signal="neutral", weight=0))
    return evidence


def cross_check(ent: Entities, facts: Dict[str, Any], evidence: List[Evidence]) -> List[Contradiction]:
    out: List[Contradiction] = []
    ids = {e.id for e in evidence}
    company_real = bool(facts.get("maps_found")) and bool(facts.get("official_domain"))
    ed = email_domain(ent.contact_email)
    off = facts.get("official_domain") or ""
    alt_ok = alt_domain_ok(ent, facts)
    off_mismatch = bool(ed) and (ed in FREE_EMAIL or (bool(off) and not facts.get("email_matches_official") and not alt_ok))

    if ed and ed not in FREE_EMAIL and off and not facts.get("email_matches_official") and not alt_ok:
        out.append(Contradiction(
            id="c-email-domain", title="Recruiter email is not on the official domain",
            detail=f"The sender uses {ed} but the company's real site is {off}. Look-alike domains are a classic impersonation trick.",
            evidence_ids=[i for i in ("google-10", "google-20") if i in ids], weight=-20))

    # Real company, but this specific offer does not trace back to it. Scammers often copy a genuine listing, so a
    # sender domain the web has never seen is enough even when the role itself is listed.
    untraceable = facts.get("jobs_found") is False or facts.get("sender_domain_unknown")
    if ent.kind == "job_offer" and company_real and untraceable and off_mismatch:
        why = ("the recruiter writes from a domain Google has never seen" if facts.get("sender_domain_unknown")
               else "the role is not in its public listings and the recruiter writes from an unrelated email domain")
        out.append(Contradiction(
            id="x-impersonation",
            title="Real company, but this offer does not trace back to it",
            detail=f"The company exists (Maps + official site), yet {why}. This pattern matches impersonation of a genuine brand.",
            evidence_ids=[i for i in ("google_maps-1", "google_jobs-1", "google-11", "google-20") if i in ids], weight=-20))

    # Nothing verifiable at all. Each absence is already scored by its own engine, so this only explains the pattern.
    # "official_domain" is only in facts when the website search actually ran: a timeout is "unknown", not "absent".
    if ent.company and facts.get("maps_found") is False and facts.get("official_domain", None) == "" and facts.get("jobs_found") in (False, None):
        out.append(Contradiction(
            id="x-ghost",
            title="Company leaves no verifiable footprint",
            detail="No Maps listing, no official website and no public listings were found for this name across three independent engines.",
            evidence_ids=[i for i in ("google_maps-1", "google-10", "google_jobs-1") if i in ids], weight=0))

    # Complaints while the brand looks strong -> consistent with impersonation, not necessarily the brand's fault.
    if facts.get("impersonation_advisory") and company_real:
        out.append(Contradiction(
            id="x-brand-abuse",
            title="Genuine brand that is actively impersonated",
            detail="Scam advisories exist for this brand. Treat any offer as unverified until confirmed via the company's official careers page.",
            evidence_ids=[i for i in ("google-2",) if i in ids], weight=-4))
    return out


# Evidence that only says "we could not find X" (as opposed to "we found something wrong").
ABSENCE_IDS = {"google_maps-1", "google-10", "google-link"}


def _is_absence(e: Evidence) -> bool:
    # google_maps-1 is also used for "listed, but rated 1.8", which is a real warning, hence the title check
    return e.id in ABSENCE_IDS and e.title.startswith(("No ", "Google has no"))


def active_warning(evidence: List[Evidence], contradictions: List[Contradiction]) -> bool:
    return (any(e.weight < 0 and not _is_absence(e) for e in evidence)
            or any(c.weight < 0 for c in contradictions))


def score(evidence: List[Evidence], contradictions: List[Contradiction]) -> int:
    s = 50 + sum(e.weight for e in evidence) + sum(c.weight for c in contradictions)
    return max(0, min(100, s))


def verdict(s: int) -> str:
    if s >= 75:
        return "likely_genuine"
    if s >= 50:
        return "verify"
    if s >= 30:
        return "suspicious"
    return "likely_scam"


def confidence(engines_ok: int, engines_tried: int) -> str:
    if engines_tried == 0:
        return "low"
    r = engines_ok / engines_tried
    if engines_ok >= 4 and r >= 0.8:
        return "high"
    if engines_ok >= 2:
        return "medium"
    return "low"
