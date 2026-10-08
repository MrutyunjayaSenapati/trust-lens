"""One collector per SerpApi engine. Each turns raw search data into scored Evidence."""
import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import Contradiction, Entities, Evidence, Source
from .serp import SerpClient
from .util import (addr_overlap, domain_contains_company, domain_of, email_domain, name_match,
                   FREE_EMAIL)

SCAM_RE = re.compile(r"\b(scam|scams|scammer|fraud|fraudulent|fake|cheat|cheated|cheating|complaints?|blacklisted?|phishing|ponzi|duped|racket)\b", re.I)
IMPERSONATION_RE = re.compile(r"(in the name of|impersonat|fake (job|offer|recruit|email|website|letter|mail)|fraudulent (job|offer|email|recruit)|beware of|fraud alert|do not fall)", re.I)
RESIDENTIAL = ("apartment", "residential", "house", "flat", "home", "villa", "pg ", "hostel")


@dataclass
class Ctx:
    text: str
    ent: Entities
    serp: SerpClient
    image_url: Optional[str] = None
    facts: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Out:
    engine: str
    evidence: List[Evidence] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    had_data: bool = False
    error: Optional[str] = None


def _ev(engine, n, title, detail, signal="neutral", weight=0, sources=None) -> Evidence:
    return Evidence(id=f"{engine}-{n}", engine=engine, title=title, detail=detail, signal=signal,
                    weight=weight, sources=[Source(title=t, url=u) for t, u in (sources or []) if u][:4])


# --- Google Search: scam reports ---------------------------------------------------------------
async def scam_reports(ctx: Ctx) -> Out:
    out = Out("google")
    c = ctx.ent.company
    if not c:
        return out
    data = await ctx.serp.search("google", q=f'"{c}" scam OR fraud OR fake OR complaint', gl="in", hl="en", num=10)
    res = data.get("organic_results", [])
    out.had_data = bool(res)
    complaints, advisories = [], []
    for r in res:
        blob = f"{r.get('title', '')} {r.get('snippet', '')}"
        if not name_match(blob, c, 0.5):
            continue
        if IMPERSONATION_RE.search(blob):
            advisories.append((r.get("title", ""), r.get("link", "")))
        elif SCAM_RE.search(blob):
            complaints.append((r.get("title", ""), r.get("link", "")))
    ctx.facts["complaints"] = len(complaints)
    if len(complaints) >= 3:
        out.evidence.append(_ev("google", 1, f"{len(complaints)} scam/complaint reports name this company",
                                "Multiple independent pages describe fraud or complaints involving this exact name.",
                                "negative", -25, complaints))
    elif complaints:
        out.evidence.append(_ev("google", 1, f"{len(complaints)} scam/complaint report(s) found",
                                "Some pages mention this name together with scam/complaint wording; read them before trusting.",
                                "negative", -12, complaints))
    else:
        out.evidence.append(_ev("google", 1, "No scam reports surfaced", "Search found no pages tying this name to fraud. Weak positive: absence of reports is not proof.",
                                "positive", 4))
    if advisories:
        ctx.facts["impersonation_advisory"] = True
        out.evidence.append(_ev("google", 2, "Brand is warned about as being impersonated",
                                "Pages warn that fake offers circulate in this brand's name. Verify through the company's official channel only.",
                                "negative", -6, advisories))
    return out


# --- Google News ----------------------------------------------------------------------------------
async def news(ctx: Ctx) -> Out:
    out = Out("google_news")
    c = ctx.ent.company
    if not c:
        return out
    data = await ctx.serp.search("google_news", q=f'"{c}" fraud OR scam OR arrested OR FIR', gl="in", hl="en")
    res = data.get("news_results", [])
    out.had_data = bool(res)
    hits = []
    for r in res:
        title = r.get("title", "")
        if name_match(title, c, 0.5) and SCAM_RE.search(title + " " + r.get("snippet", "")):
            hits.append((f"{title} ({(r.get('source') or {}).get('name', '')})", r.get("link", "")))
    ctx.facts["news_hits"] = len(hits)
    if hits:
        out.evidence.append(_ev("google_news", 1, f"{len(hits)} news article(s) link this name to fraud",
                                "News coverage mentions this name alongside fraud/arrest wording.", "negative",
                                -18 if len(hits) > 1 else -12, hits))
    else:
        out.evidence.append(_ev("google_news", 1, "No fraud-related news", "No news articles tie this name to fraud.", "neutral", 0))
    return out


# --- Google Maps: does the physical place exist? ----------------------------------------------------
async def maps(ctx: Ctx) -> Out:
    out = Out("google_maps")
    e = ctx.ent
    if not e.company:
        return out
    q = f"{e.company} {e.city or ''}".strip()
    data = await ctx.serp.search("google_maps", q=q, type="search", hl="en", gl="in")
    places = data.get("local_results") or ([data["place_results"]] if data.get("place_results") else [])
    out.had_data = True
    best = next((p for p in places if name_match(p.get("title", ""), e.company)), None)
    ctx.facts["maps_found"] = bool(best)
    if not best:
        out.evidence.append(_ev("google_maps", 1, "No Google Maps listing for this company",
                                f"Searched Maps for “{q}” and found no matching business. Real companies with offices are almost always listed.",
                                "negative", -15))
        return out
    rating, reviews = best.get("rating"), best.get("reviews") or 0
    addr = best.get("address", "")
    ctx.facts["maps_address"] = addr
    ctx.facts["maps_type"] = str(best.get("type", ""))
    w, sig = 10, "positive"
    if reviews >= 50 and (rating or 0) >= 3.5:
        w = 14
    if reviews >= 10 and rating is not None and rating < 2.5:
        w, sig = -10, "negative"
    out.evidence.append(_ev("google_maps", 1, f"Listed on Google Maps: {best.get('title')}",
                            f"{addr or 'address n/a'} · rating {rating} from {reviews} reviews · type: {best.get('type', 'n/a')}", sig, w))
    ptype = (best.get("type") or "").lower()
    if any(r in ptype for r in RESIDENTIAL):
        out.contradictions.append(Contradiction(id="c-maps-resid", title="Listed as a residential place",
                                                detail=f"Maps classifies the address as “{best.get('type')}”, not an office.",
                                                evidence_ids=["google_maps-1"], weight=-12))
    if e.claimed_address and addr and addr_overlap(e.claimed_address, addr) < 0.25:
        out.contradictions.append(Contradiction(id="c-maps-addr", title="Claimed address does not match Maps",
                                                detail=f"Message says “{e.claimed_address}”, Maps shows “{addr}”.",
                                                evidence_ids=["google_maps-1"], weight=-15))
    return out


# --- Google Jobs ----------------------------------------------------------------------------------------
async def jobs(ctx: Ctx) -> Out:
    out = Out("google_jobs")
    e = ctx.ent
    if e.kind != "job_offer" or not e.company:
        return out
    q = f"{e.role or ''} {e.company}".strip()
    data = await ctx.serp.search("google_jobs", q=q, gl="in", hl="en")
    res = data.get("jobs_results", [])
    out.had_data = True
    matches = [j for j in res if name_match(j.get("company_name", ""), e.company)]
    ctx.facts["jobs_found"] = bool(matches)
    if matches:
        j = matches[0]
        out.evidence.append(_ev("google_jobs", 1, f"Company hires publicly: {j.get('title')}",
                                f"Found {len(matches)} public listing(s) by this company ({j.get('via', '')}, {j.get('location', '')}).",
                                "positive", 14))
    else:
        out.evidence.append(_ev("google_jobs", 1, "No public job listing for this company",
                                f"Google Jobs shows no listing for “{q}”. Small firms and referrals can be unlisted, so this is a moderate signal.",
                                "negative", -10))
    return out


# --- Google Search: official presence + email domain ------------------------------------------------------
async def official_presence(ctx: Ctx) -> Out:
    out = Out("google_official")
    out.engine = "google"
    e = ctx.ent
    if not e.company:
        return out
    data = await ctx.serp.search("google", q=f"{e.company} official website", gl="in", hl="en", num=8)
    res = data.get("organic_results", [])
    out.had_data = bool(res)
    # The official site is the company-named domain that shows up most often (ties: highest ranked). Taking the first
    # match picks side sites such as a foundation microsite over the main domain.
    seen: Dict[str, int] = {}
    for r in res:
        d = domain_of(r.get("link", ""))
        if d and domain_contains_company(d, e.company):
            seen[d] = seen.get(d, 0) + 1
    order = list(seen)
    official = max(order, key=lambda d: (seen[d], -order.index(d))) if order else ""
    ctx.facts["official_domain"] = official
    ctx.facts["official_domains"] = order
    n = 10
    if not official:
        out.evidence.append(_ev("google", n, "No official website found",
                                "Top search results contain no domain that matches the company name.", "negative", -10))
    else:
        out.evidence.append(_ev("google", n, f"Official website found: {official}", "A domain matching the company name ranks in search.", "positive", 8,
                                [(official, f"https://{official}")]))
    ed = email_domain(e.contact_email)
    if ed:
        if ed in FREE_EMAIL:
            out.evidence.append(_ev("google", n + 1, f"Contact uses a free email ({ed})",
                                    "Companies hire from their own domain; free webmail for an “HR” is a common scam trait.", "negative", -15))
        elif official and any(ed == d or ed.endswith("." + d) or d.endswith("." + ed) for d in ctx.facts["official_domains"]):
            out.evidence.append(_ev("google", n + 1, "Email domain matches the official site",
                                    f"{ed} is the company's own domain.", "positive", 15))
        elif official:
            out.contradictions.append(Contradiction(
                id="c-email-domain", title="Recruiter email is not on the official domain",
                detail=f"The sender uses {ed} but the company's real site is {official}. Look-alike domains are a classic impersonation trick.",
                evidence_ids=[f"google-{n}"], weight=-20))
    return out


# --- Google Shopping: is the deal real? ---------------------------------------------------------------------
async def shopping(ctx: Ctx) -> Out:
    out = Out("google_shopping")
    e = ctx.ent
    if e.kind != "deal" or not e.product:
        return out
    data = await ctx.serp.search("google_shopping", q=e.product, gl="in", hl="en")
    prices = [r["extracted_price"] for r in data.get("shopping_results", []) if isinstance(r.get("extracted_price"), (int, float))]
    out.had_data = bool(prices)
    if len(prices) < 3:
        return out
    med = statistics.median(prices)
    srcs = [(f"{r.get('source', '')} ₹{r.get('extracted_price')}", r.get("link", "")) for r in data["shopping_results"][:3]]
    out.evidence.append(_ev("google_shopping", 1, f"Market median price ₹{med:,.0f}",
                            f"Based on {len(prices)} live listings (range ₹{min(prices):,.0f}–₹{max(prices):,.0f}).", "neutral", 0, srcs))
    if e.claimed_price:
        if e.claimed_price < 0.5 * med:
            out.contradictions.append(Contradiction(id="c-too-cheap", title="Price is far below market",
                                                    detail=f"Offered at ₹{e.claimed_price:,.0f} vs market median ₹{med:,.0f}; if it is too good to be true it usually is.",
                                                    evidence_ids=["google_shopping-1"], weight=-22))
        elif e.claimed_price <= 1.1 * med:
            out.evidence.append(_ev("google_shopping", 2, "Price is in the normal market range", f"₹{e.claimed_price:,.0f} vs median ₹{med:,.0f}.", "positive", 6))
    if e.claimed_original_price and e.claimed_original_price > 1.3 * med:
        out.contradictions.append(Contradiction(id="c-fake-mrp", title="“Original price” is inflated",
                                                detail=f"Claimed original ₹{e.claimed_original_price:,.0f}, but it sells for about ₹{med:,.0f} in the market, so the discount is fake.",
                                                evidence_ids=["google_shopping-1"], weight=-18))
    return out


# --- Google Lens: reused / stolen image ------------------------------------------------------------------------
async def lens(ctx: Ctx) -> Out:
    out = Out("google_lens")
    if not ctx.image_url:
        return out
    data = await ctx.serp.search("google_lens", url=ctx.image_url, hl="en")
    matches = data.get("visual_matches", [])
    out.had_data = bool(matches)
    domains = {domain_of(m.get("link", "")) for m in matches if m.get("link")}
    domains.discard("")
    if len(domains) >= 5:
        out.evidence.append(_ev("google_lens", 1, f"Image appears on {len(domains)} unrelated sites",
                                "The picture is widely reused online, so it is probably stock or stolen rather than original.", "negative", -10,
                                [(m.get("title", ""), m.get("link", "")) for m in matches[:3]]))
    else:
        out.evidence.append(_ev("google_lens", 1, "Image is not widely reused", f"Visual search found {len(domains)} other site(s).", "neutral", 0))
    return out


ALL = [scam_reports, news, maps, jobs, official_presence, shopping, lens]
