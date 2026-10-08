"""Cross-source reasoning: judgments that only make sense once every engine has answered."""
from typing import Any, Dict, List

from .models import Contradiction, Entities, Evidence
from .util import FREE_EMAIL, email_domain, is_alt_domain

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


def reconcile(ent: Entities, facts: Dict[str, Any], evidence: List[Evidence]) -> List[Evidence]:
    """Re-weigh single-engine evidence in the light of the others. Every change is written into the evidence detail,
    so the score ledger still explains each point."""
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
    # traces back to the company through its email domain; otherwise anyone could borrow "Amazon" and score well.
    traced = facts.get("email_matches_official") or alt_domain_ok(ent, facts)
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
