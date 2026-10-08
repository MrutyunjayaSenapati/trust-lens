import asyncio
from typing import Any, AsyncIterator, Dict, List

from . import collectors as C
from .extraction import apply_resolved, extract, red_flags
from .models import (Contradiction, Evidence, GraphEdge, GraphNode, InvestigateRequest, Result, Source)
from .reasoner import active_warning, confidence, cross_check, reconcile, score, verdict
from .serp import SerpClient
from .synthesis import synthesize
from .urlintel import find_url, is_link_only, resolve
from .util import domain_of

ENGINE_LABEL = {
    "google": "Google Search", "google_news": "Google News", "google_maps": "Google Maps",
    "google_jobs": "Google Jobs", "google_shopping": "Google Shopping", "google_lens": "Google Lens",
    "text-analysis": "Text analysis",
}


def _planned(ctx: C.Ctx) -> List[Any]:
    e = ctx.ent
    plan = []
    if e.company:
        plan += [C.scam_reports, C.news, C.maps, C.official_presence]
    if e.kind == "job_offer" and e.company:
        plan.append(C.jobs)
    ed = C.email_domain(e.contact_email)
    if ed and ed not in C.FREE_EMAIL:  # free webmail is judged without a search
        plan.append(C.sender_domain)
    if C.digits10(e.phone):
        plan.append(C.phone_reports)
    if e.kind == "deal" and e.product:
        plan.append(C.shopping)
    if ctx.image_url:
        plan.append(C.lens)
    return plan


def build_graph(subject: str, evidence: List[Evidence], contradictions: List[Contradiction]):
    nodes = [GraphNode(id="subject", label=subject, type="subject")]
    edges: List[GraphEdge] = []
    seen = set()
    for ev in evidence:
        if ev.engine not in seen:
            seen.add(ev.engine)
            nodes.append(GraphNode(id=f"eng:{ev.engine}", label=ENGINE_LABEL.get(ev.engine, ev.engine), type="engine"))
            edges.append(GraphEdge(source="subject", target=f"eng:{ev.engine}", kind="engine"))
        nodes.append(GraphNode(id=ev.id, label=ev.title, type="evidence", signal=ev.signal))
        edges.append(GraphEdge(source=f"eng:{ev.engine}", target=ev.id, kind="evidence"))
    known = {n.id for n in nodes}
    for c in contradictions:
        nodes.append(GraphNode(id=c.id, label=c.title, type="contradiction", signal="negative"))
        linked = [i for i in c.evidence_ids if i in known]
        for i in linked:
            edges.append(GraphEdge(source=c.id, target=i, kind="conflict"))
        if not linked:
            edges.append(GraphEdge(source="subject", target=c.id, kind="conflict"))
    return nodes, edges


async def run(req: InvestigateRequest) -> AsyncIterator[Dict[str, Any]]:
    text = (req.text or "").strip()
    if not text and not req.image_base64:
        yield {"type": "error", "message": "Paste the message or upload a screenshot first."}
        return

    serp = SerpClient()
    yield {"type": "stage", "stage": "extract", "message": "Reading the message and extracting who/what/where…"}
    resolved, source_note, link_ev = None, None, []
    extract_text = text
    if is_link_only(text):
        url = find_url(text)
        yield {"type": "stage", "stage": "link", "message": "That is a link, so I am asking Google (via SerpApi) what it points to…"}
        try:
            resolved = await resolve(url, serp)
        except Exception as exc:  # a failed lookup must not sink the investigation
            yield {"type": "stage", "stage": "warn", "message": f"Link lookup failed: {(str(exc) or type(exc).__name__)[:120]}"}
        if resolved and resolved.found:
            yield {"type": "stage", "stage": "link", "message": f"Google knows this page as: {resolved.title}"}
            extract_text = f"{text}\n\nGoogle lists this page as: {resolved.title}\nSnippet: {resolved.snippet}"
            source_note = f"Link resolved via Google: {resolved.title}"
            link_ev.append(Evidence(id="google-link", engine="google", title="Link is indexed by Google",
                                    detail=f"Google lists this page as “{resolved.title}”. Being listed does not prove an offer is genuine, but a link Google has never seen is a warning sign.",
                                    signal="positive", weight=4, sources=[Source(title=resolved.title, url=resolved.link or resolved.url)]))
        elif resolved and resolved.url_words:
            # A new posting on a job site: not indexed yet, but its address names the role and company.
            yield {"type": "stage", "stage": "link", "message": f"Not indexed by Google yet; the link's address reads: {resolved.url_words}"}
            extract_text = f"{text}\n\nJob posting on {domain_of(resolved.url)}. The link's address reads: {resolved.url_words}"
            source_note = f"Not indexed by Google yet. Role and company read from the link's address: “{resolved.url_words}”."
            link_ev.append(Evidence(id="google-link", engine="google", title="Posting is too new for Google to have indexed it",
                                    detail="Normal for a posting from the last day or two. The role and company were read from the link itself, "
                                           "so the company can still be checked, but the posting itself cannot be confirmed yet.",
                                    signal="neutral", weight=0))
        elif resolved and resolved.on_job_site:
            source_note = f"Google has not indexed this {domain_of(resolved.url)} posting yet, and the link itself does not name the company."
            link_ev.append(Evidence(id="google-link", engine="google", title="Posting not indexed by Google yet",
                                    detail="Common for postings from the last day or two, so this is not held against it. Paste the posting "
                                           "text (company, role, recruiter's email) and TrustLens can check the company.",
                                    signal="neutral", weight=0))
        else:
            source_note = "This link could not be matched to any page Google knows about."
            link_ev.append(Evidence(id="google-link", engine="google", title="Google has no record of this link",
                                    detail="Searching for the link returned nothing. Brand-new, expired or fake pages all look like this, so it is only a mild warning. Paste the message text too for a fuller check.",
                                    signal="negative", weight=-3))

    ent = await extract(extract_text, req.image_base64, req.image_mime)
    ent = apply_resolved(ent, resolved)
    if req.image_base64 and not ent.transcript:
        yield {"type": "stage", "stage": "warn", "message": "Could not read the screenshot right now. Paste the message text for a full check."}
    yield {"type": "entities", "entities": ent.model_dump()}

    ctx = C.Ctx(text=text, ent=ent, serp=serp, image_url=req.image_url)
    if resolved and resolved.found and resolved.on_job_site:
        ctx.facts["job_site_listing"] = domain_of(resolved.url)  # Google has indexed this posting on a job site
    evidence: List[Evidence] = []
    contradictions: List[Contradiction] = []

    flags = link_ev + red_flags(f"{text}\n{ent.transcript}", ent)
    for f in flags:
        evidence.append(f)
        yield {"type": "evidence", "item": f.model_dump()}

    plan = _planned(ctx)
    engine_of = {"scam_reports": "google", "official_presence": "google", "sender_domain": "google", "phone_reports": "google",
                 "news": "google_news", "maps": "google_maps",
                 "jobs": "google_jobs", "shopping": "google_shopping", "lens": "google_lens"}
    keys = sorted({engine_of[p.__name__] for p in plan})
    names = [ENGINE_LABEL[k] for k in keys]
    yield {"type": "stage", "stage": "plan", "engines": keys,
           "message": f"Investigation plan: {', '.join(names)}" if names else "No company or product found, so only text patterns can be checked."}

    async def guarded(fn):
        try:
            return await fn(ctx)
        except Exception as exc:  # one broken engine must not sink the investigation
            return C.Out(engine=fn.__name__, error=str(exc)[:160])

    ok = 0
    tasks = [asyncio.create_task(guarded(fn)) for fn in plan]
    for fut in asyncio.as_completed(tasks):
        out = await fut
        if out.error:
            yield {"type": "stage", "stage": "warn", "message": f"{out.engine} unavailable: {out.error}"}
            continue
        if out.had_data:
            ok += 1
        for ev in out.evidence:
            evidence.append(ev)
            yield {"type": "evidence", "item": ev.model_dump()}
        for c in out.contradictions:
            contradictions.append(c)
            yield {"type": "contradiction", "item": c.model_dump()}

    yield {"type": "stage", "stage": "reason", "message": "Cross-checking sources for contradictions…"}
    evidence = reconcile(ent, ctx.facts, evidence)
    for c in cross_check(ent, ctx.facts, evidence):
        contradictions.append(c)
        yield {"type": "contradiction", "item": c.model_dump()}

    s = score(evidence, contradictions)
    v = verdict(s)
    # Nothing could be searched and nothing in the text is alarming: say "can't tell", never "suspicious".
    # (e.g. a brand-new LinkedIn link that Google has not indexed yet)
    if not plan and not contradictions and all(abs(e.weight) <= 4 for e in evidence):
        v = "verify"
    # "Likely scam" needs an active warning sign (fee demand, scam reports, a contradiction...). Missing footprint
    # alone (no Maps, no website) only makes a small or new firm unverifiable, so it stops at "suspicious".
    if v == "likely_scam" and not active_warning(evidence, contradictions):
        v = "suspicious"
    yield {"type": "stage", "stage": "write", "message": f"Trust score {s}/100. Writing the briefing…"}
    syn = await synthesize(v, s, ent, evidence, contradictions)
    nodes, edges = build_graph(ent.company or "Submission", evidence, contradictions)
    engines_used = sorted({e.engine for e in evidence})
    result = Result(
        score=s, verdict=v, confidence=confidence(ok, len(plan)), entities=ent, evidence=evidence,
        contradictions=contradictions, graph_nodes=nodes, graph_edges=edges, engines_used=engines_used,
        live_calls=serp.live_calls, cache_hits=serp.cache_hits, source_note=source_note, **syn)
    yield {"type": "result", "result": result.model_dump()}
