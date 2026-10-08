"""Cross-source reasoning: contradictions that only appear when engines are compared."""
from typing import Any, Dict, List

from .models import Contradiction, Entities, Evidence
from .util import FREE_EMAIL, email_domain


def cross_check(ent: Entities, facts: Dict[str, Any], evidence: List[Evidence]) -> List[Contradiction]:
    out: List[Contradiction] = []
    ids = {e.id for e in evidence}
    company_real = bool(facts.get("maps_found")) and bool(facts.get("official_domain"))
    ed = email_domain(ent.contact_email)
    off = facts.get("official_domain") or ""
    off_mismatch = bool(ed) and (ed in FREE_EMAIL or (off and not (ed == off or ed.endswith("." + off))))

    # Real company, but this specific offer does not trace back to it.
    if ent.kind == "job_offer" and company_real and facts.get("jobs_found") is False and off_mismatch:
        out.append(Contradiction(
            id="x-impersonation",
            title="Real company, but this offer does not trace back to it",
            detail="The company exists (Maps + official site), yet the role is not in its public listings and the recruiter writes from an unrelated email domain. This pattern matches impersonation of a genuine brand.",
            evidence_ids=[i for i in ("google_maps-1", "google_jobs-1", "google-11") if i in ids], weight=-20))

    # Nothing verifiable at all.
    if ent.company and facts.get("maps_found") is False and not facts.get("official_domain") and facts.get("jobs_found") in (False, None):
        out.append(Contradiction(
            id="x-ghost",
            title="Company leaves no verifiable footprint",
            detail="No Maps listing, no official website and no public listings were found for this name across three independent engines.",
            evidence_ids=[i for i in ("google_maps-1", "google-10", "google_jobs-1") if i in ids], weight=-15))

    # Complaints while the brand looks strong -> consistent with impersonation, not necessarily the brand's fault.
    if facts.get("impersonation_advisory") and company_real:
        out.append(Contradiction(
            id="x-brand-abuse",
            title="Genuine brand that is actively impersonated",
            detail="Scam advisories exist for this brand. Treat any offer as unverified until confirmed via the company's official careers page.",
            evidence_ids=[i for i in ("google-2",) if i in ids], weight=-4))
    return out


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
