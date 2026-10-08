import json
from typing import List

from . import gemini
from .models import Contradiction, Entities, Evidence

PROMPT = """You write the final briefing of a scam-investigation tool for people in India.
The trust score and verdict were ALREADY computed from evidence. Do not change or second-guess them.
Use ONLY the evidence given; never add outside facts. Be calm, specific and plain-spoken.

Return ONE JSON object:
explanation: 3-4 sentences explaining why the verdict was reached, citing the strongest evidence.
explanation_hi: the same explanation in simple, natural Hindi (Devanagari), not a literal translation.
next_steps: array of exactly 3 short, concrete actions for the user.
next_steps_hi: the same 3 actions in simple Hindi (Devanagari).
warning_en: a 2-3 sentence message the user can forward to a family/friends WhatsApp group (plain text, no markdown).
warning_hi: the same warning in simple Hindi (Devanagari).

If the verdict is "likely_genuine" or "verify", keep the tone neutral and stress verifying through official channels.

VERDICT: {verdict}   SCORE: {score}/100
SUBJECT: {entities}
EVIDENCE: {evidence}
CONTRADICTIONS: {contradictions}
"""

LABEL = {
    "likely_genuine": ("looks genuine", "असली लगता है"),
    "verify": ("could not be fully verified", "पूरी तरह सत्यापित नहीं हो पाया"),
    "suspicious": ("looks suspicious", "संदिग्ध लगता है"),
    "likely_scam": ("looks like a scam", "धोखाधड़ी जैसा लगता है"),
}


STEPS_HI = ["कोई पैसा न दें और OTP, आधार या बैंक की जानकारी साझा न करें।",
            "संदेश में दिए संपर्क पर नहीं, कंपनी की आधिकारिक वेबसाइट या करियर पेज से पुष्टि करें।",
            "धोखाधड़ी की शिकायत cybercrime.gov.in पर करें या 1930 पर कॉल करें।"]


def fallback(verdict: str, ent: Entities, evidence: List[Evidence], contradictions: List[Contradiction]) -> dict:
    name = ent.company or "This message"
    en, hi = LABEL[verdict]
    neg = [c.title for c in contradictions] + [e.title for e in evidence if e.signal == "negative"]
    pos = [e.title for e in evidence if e.signal == "positive"]
    why = "; ".join(neg[:3]) if neg else "; ".join(pos[:3]) or "limited public information was found"
    steps = ["Do not pay any money or share OTPs, Aadhaar or bank details.",
             "Verify through the company's official website or careers page, not the contact in the message.",
             "Report suspected fraud at cybercrime.gov.in or call 1930."]
    return {
        "explanation": f"{name} {en}. Key findings: {why}.",
        "next_steps": steps,
        "explanation_hi": f"{name} {hi}। मुख्य कारण ऊपर साक्ष्य सूची में दिए गए हैं।",
        "next_steps_hi": STEPS_HI,
        "warning_en": f"Heads up: I checked this offer from {name} and it {en}. {why}. Please don't pay or share personal details; verify on the official website first.",
        "warning_hi": f"सावधान: मैंने {name} का यह ऑफ़र जाँचा, यह {hi}। कृपया पैसे न दें और निजी जानकारी साझा न करें; पहले आधिकारिक वेबसाइट पर जाँच करें।",
    }


async def synthesize(verdict: str, score: int, ent: Entities, evidence: List[Evidence], contradictions: List[Contradiction]) -> dict:
    base = fallback(verdict, ent, evidence, contradictions)
    compact_ev = [{"engine": e.engine, "title": e.title, "detail": e.detail, "signal": e.signal} for e in evidence]
    compact_c = [{"title": c.title, "detail": c.detail} for c in contradictions]
    raw = await gemini.generate_json(PROMPT.format(
        verdict=verdict, score=score, entities=ent.model_dump_json(exclude_none=True),
        evidence=json.dumps(compact_ev, ensure_ascii=False), contradictions=json.dumps(compact_c, ensure_ascii=False)))
    if not raw:
        return base
    steps = raw.get("next_steps")
    return {
        "explanation": str(raw.get("explanation") or base["explanation"]),
        "next_steps": [str(s) for s in steps][:3] if isinstance(steps, list) and steps else base["next_steps"],
        "explanation_hi": str(raw.get("explanation_hi") or base["explanation_hi"]),
        "next_steps_hi": [str(s) for s in raw["next_steps_hi"]][:3] if isinstance(raw.get("next_steps_hi"), list) and raw["next_steps_hi"] else base["next_steps_hi"],
        "warning_en": str(raw.get("warning_en") or base["warning_en"]),
        "warning_hi": str(raw.get("warning_hi") or base["warning_hi"]),
    }
